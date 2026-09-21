from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

from .cua_binding import CuaBinding
from .errors import ControlPlaneError, FailureCode
from .orchestrator import BrowserAdapter


@dataclass(slots=True)
class ManagedSession:
    session_id: str
    initial_url: str
    adapter: BrowserAdapter
    created_at: float
    mode: str = "isolated"
    cua_binding: CuaBinding | None = None

    def to_dict(self) -> dict[str, object]:
        snapshot = self.adapter.snapshot()
        return {
            "session_id": self.session_id,
            "initial_url": self.initial_url,
            "current_url": snapshot.url,
            "page_revision": snapshot.revision,
            "created_at": self.created_at,
            "mode": self.mode,
            "adapter": snapshot.metadata.get("adapter", "unknown"),
            "cua_binding": self.cua_binding is not None,
        }


AdapterFactory = Callable[[str, str], BrowserAdapter]
CuaBindingFactory = Callable[[str, str], CuaBinding | None]


class BrowserSessionRegistry:
    def __init__(
        self,
        adapter_factory: AdapterFactory,
        *,
        cua_binding_factory: CuaBindingFactory | None = None,
    ) -> None:
        self._adapter_factory = adapter_factory
        self._cua_binding_factory = cua_binding_factory
        self._sessions: dict[str, ManagedSession] = {}
        self._lock = threading.RLock()

    def create(self, *, session_id: str, initial_url: str) -> ManagedSession:
        if not session_id.strip():
            raise ValueError("session_id is required")
        with self._lock:
            if session_id in self._sessions:
                raise ControlPlaneError(
                    FailureCode.BLOCKED_SESSION_ALREADY_EXISTS,
                    "Browser session already exists",
                    {"session_id": session_id},
                )
            adapter = self._adapter_factory(session_id, initial_url)
            start = getattr(adapter, "start", None)
            try:
                if callable(start):
                    start()
                open_initial_url = getattr(adapter, "open_initial_url", None)
                if callable(open_initial_url):
                    open_initial_url(initial_url)
            except Exception:
                close = getattr(adapter, "close", None)
                if callable(close):
                    close()
                raise
            managed = ManagedSession(
                session_id=session_id,
                initial_url=initial_url,
                adapter=adapter,
                created_at=time.time(),
                cua_binding=(
                    self._cua_binding_factory(session_id, initial_url)
                    if self._cua_binding_factory is not None
                    else None
                ),
            )
            self._sessions[session_id] = managed
            return managed

    def get(self, session_id: str) -> ManagedSession:
        with self._lock:
            try:
                return self._sessions[session_id]
            except KeyError as exc:
                raise ControlPlaneError(
                    FailureCode.BLOCKED_SESSION_NOT_FOUND,
                    "Browser session does not exist",
                    {"session_id": session_id},
                ) from exc

    def bind_cua(self, *, session_id: str, binding: CuaBinding) -> ManagedSession:
        """Attach a trusted host-created CUA binding outside the MCP surface.

        The registry deliberately accepts a fully constructed binding only.
        It never accepts PID/window/tab values from a browser action request.
        """

        if binding.session_id != session_id:
            raise ControlPlaneError(
                FailureCode.BLOCKED_CUA_SESSION_BINDING_MISMATCH,
                "CUA binding belongs to a different browser session",
                {"binding_session_id": binding.session_id, "session_id": session_id},
            )
        with self._lock:
            managed = self.get(session_id)
            if managed.cua_binding is not None and managed.cua_binding != binding:
                raise ControlPlaneError(
                    FailureCode.BLOCKED_CUA_SESSION_BINDING_MISMATCH,
                    "An exact CUA binding is already attached to this browser session",
                    {"session_id": session_id},
                )
            managed.cua_binding = binding
            return managed

    def close(self, session_id: str) -> bool:
        with self._lock:
            managed = self._sessions.pop(session_id, None)
        if managed is None:
            return False
        close = getattr(managed.adapter, "close", None)
        if callable(close):
            close()
        return True

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def close_all(self) -> None:
        with self._lock:
            ids = list(self._sessions)
        for session_id in ids:
            self.close(session_id)
