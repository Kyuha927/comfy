from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from dataclasses import dataclass

from .errors import ControlPlaneError, FailureCode
from .models import ActionRequest, EngineKind


_READ_ONLY_ACTIONS = frozenset(
    {
        "health",
        "inspect",
        "query",
        "screenshot",
        "read_network",
        "read_console",
        "job_get",
        "evidence_get",
        "wait",
    }
)


def is_possible_mutation(request: ActionRequest) -> bool:
    return request.action_type not in _READ_ONLY_ACTIONS


def _scope_key(request: ActionRequest) -> str:
    payload = {
        "session_id": request.session_id,
        "action_type": request.action_type,
        "target_url": request.target_url,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class PendingMutation:
    job_id: str
    engine: EngineKind
    created_at: float


class SideEffectReconciliationRegistry:
    """Durable fail-closed record for a mutation whose final effect is unknown.

    Only trusted host code can call :meth:`reconcile`; the MCP tool catalog has
    no operation that can self-certify a pending side effect.
    """

    def __init__(self, database_path: str) -> None:
        self._conn = sqlite3.connect(database_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_side_effects (
                    job_id TEXT PRIMARY KEY,
                    scope_key TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    engine TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    reconciled_at REAL,
                    verifier_id TEXT,
                    evidence_hash TEXT
                )
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS pending_side_effects_scope_state
                ON pending_side_effects(scope_key, state)
                """
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def record_possible_mutation(
        self, *, job_id: str, request: ActionRequest, engine: EngineKind
    ) -> None:
        if not is_possible_mutation(request):
            return
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO pending_side_effects(
                    job_id, scope_key, idempotency_key, engine, state, created_at
                ) VALUES (?, ?, ?, ?, 'PENDING', ?)
                ON CONFLICT(job_id) DO NOTHING
                """,
                (
                    job_id,
                    _scope_key(request),
                    request.idempotency_key,
                    engine.value,
                    time.time(),
                ),
            )

    def mark_terminal_safe(self, job_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE pending_side_effects SET state = 'RESOLVED' WHERE job_id = ? AND state = 'PENDING'",
                (job_id,),
            )

    def require_fallback_reconciled(self, request: ActionRequest) -> None:
        if not is_possible_mutation(request):
            return
        with self._lock:
            row = self._conn.execute(
                """
                SELECT job_id, engine, created_at
                FROM pending_side_effects
                WHERE scope_key = ? AND state = 'PENDING' AND idempotency_key != ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (_scope_key(request), request.idempotency_key),
            ).fetchone()
        if row is not None:
            pending = PendingMutation(
                job_id=str(row["job_id"]),
                engine=EngineKind(str(row["engine"])),
                created_at=float(row["created_at"]),
            )
            raise ControlPlaneError(
                FailureCode.BLOCKED_SIDE_EFFECT_RECONCILIATION_REQUIRED,
                "A prior possibly-mutating action has not been independently reconciled",
                {
                    "prior_job_id": pending.job_id,
                    "prior_engine": pending.engine.value,
                    "created_at": pending.created_at,
                },
            )

    def reconcile(self, *, job_id: str, verifier_id: str, evidence_hash: str) -> None:
        if not verifier_id.strip() or not evidence_hash.strip():
            raise ValueError("Reconciliation requires a verifier ID and evidence hash")
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """
                UPDATE pending_side_effects
                SET state = 'RECONCILED', reconciled_at = ?, verifier_id = ?, evidence_hash = ?
                WHERE job_id = ? AND state = 'PENDING'
                """,
                (time.time(), verifier_id, evidence_hash, job_id),
            )
        if cursor.rowcount != 1:
            raise ControlPlaneError(
                FailureCode.BLOCKED_SIDE_EFFECT_RECONCILIATION_REQUIRED,
                "No pending possible mutation is available for trusted reconciliation",
                {"job_id": job_id},
            )
