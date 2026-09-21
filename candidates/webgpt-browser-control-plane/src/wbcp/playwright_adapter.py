from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .errors import ControlPlaneError, FailureCode
from .models import ActionRequest, BrowserSnapshot, ExecutionResult, SignalBundle
from .redaction import Redactor
from .url_guard import URLGuard


class PlaywrightUnavailable(RuntimeError):
    pass


class PlaywrightBrowserAdapter:
    """Production-oriented Playwright-owned browser adapter.

    This adapter intentionally does not use connect_over_cdp as its primary path.
    It owns the browser/context, uses an isolated context, and requires explicit
    semantic locators and postconditions. The candidate source is syntax-tested,
    but live-browser acceptance is a separate release gate.
    """

    def __init__(
        self,
        *,
        artifacts_dir: str | os.PathLike[str],
        headless: bool = True,
        storage_state_path: str | None = None,
        allow_css_locators: bool = False,
        timeout_ms: int = 30_000,
        executable_path: str | None = None,
        url_guard: URLGuard | None = None,
        trace_path: str | os.PathLike[str] | None = None,
    ) -> None:
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.storage_state_path = storage_state_path
        self.allow_css_locators = allow_css_locators
        self.timeout_ms = timeout_ms
        self.executable_path = executable_path
        self.url_guard = url_guard
        self.trace_path = Path(trace_path) if trace_path else self.artifacts_dir / "playwright-trace.zip"
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._network_events: list[dict[str, Any]] = []
        self._console_events: list[dict[str, Any]] = []
        self._security_events: list[dict[str, Any]] = []
        self._security_violation: ControlPlaneError | None = None
        self._trace_started = False
        self._redactor = Redactor()

    def start(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise PlaywrightUnavailable(
                "Install the pinned Playwright dependency and browser binaries before live use"
            ) from exc
        try:
            self._playwright = sync_playwright().start()
            launch_kwargs: dict[str, Any] = {"headless": self.headless}
            if self.executable_path:
                launch_kwargs["executable_path"] = self.executable_path
            self._browser = self._playwright.chromium.launch(**launch_kwargs)
            context_kwargs: dict[str, Any] = {
                "accept_downloads": True,
                "service_workers": "block",
            }
            if self.storage_state_path:
                state_path = Path(self.storage_state_path)
                if not state_path.exists():
                    raise FileNotFoundError(state_path)
                context_kwargs["storage_state"] = str(state_path)
            self._context = self._browser.new_context(**context_kwargs)
            self._context.set_default_timeout(self.timeout_ms)
            if self.url_guard is not None:
                self._context.route("**/*", self._route_request)
            self._context.tracing.start(screenshots=True, snapshots=True, sources=True)
            self._trace_started = True
            self._page = self._context.new_page()
            self._page.on("response", self._on_response)
            self._page.on("console", self._on_console)
        except Exception as exc:  # noqa: BLE001 - runtime/browser install boundary
            self.close()
            raise PlaywrightUnavailable(
                "Pinned Playwright runtime or browser binary is unavailable"
            ) from exc

    def open_initial_url(self, url: str) -> BrowserSnapshot:
        """Open the exact pre-authorized initial URL in the owned context."""
        self._raise_security_violation()
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        except Exception:
            self._raise_security_violation()
            raise
        self._raise_security_violation()
        return self.snapshot()

    @property
    def page(self):
        if self._page is None:
            raise RuntimeError("PlaywrightBrowserAdapter.start() has not been called")
        return self._page

    def _record_security_violation(self, exc: ControlPlaneError, *, url: str) -> None:
        if self._security_violation is None:
            self._security_violation = exc
        self._security_events.append(
            self._redactor.redact({"url": url, "failure": exc.to_dict()})
        )
        if len(self._security_events) > 100:
            del self._security_events[:-100]

    def _route_request(self, route, request) -> None:
        """Fail closed on every HTTP(S) egress, including redirect hops.

        A strict production deployment should give the guard the complete exact-host
        egress set required by the target site. Browser-internal about/data/blob URLs
        do not create network egress and are allowed.
        """
        url = str(request.url)
        if url.startswith(("about:", "data:", "blob:")):
            route.continue_()
            return
        if self.url_guard is None:
            route.abort("blockedbyclient")
            self._record_security_violation(
                ControlPlaneError(
                    FailureCode.BLOCKED_UNSAFE_URL,
                    "Live browser egress requires an explicit URLGuard",
                ),
                url=url,
            )
            return
        try:
            self.url_guard.validate(url)
        except ControlPlaneError as exc:
            route.abort("blockedbyclient")
            redirected_from = getattr(request, "redirected_from", None)
            if redirected_from is not None:
                exc = ControlPlaneError(
                    FailureCode.BLOCKED_REDIRECT_SCOPE_ESCAPE,
                    "Redirect left the authorized browser egress scope",
                    {
                        "from": str(redirected_from.url),
                        "to": url,
                        "cause": exc.to_dict(),
                    },
                )
            self._record_security_violation(exc, url=url)
            return
        route.continue_()

    def _raise_security_violation(self) -> None:
        if self._security_violation is not None:
            exc = self._security_violation
            self._security_violation = None
            raise exc

    def _on_response(self, response) -> None:
        self._network_events.append(
            self._redactor.redact(
                {
                    "url": response.url,
                    "status": response.status,
                    "method": response.request.method,
                    "resource_type": response.request.resource_type,
                }
            )
        )
        if len(self._network_events) > 500:
            del self._network_events[:-500]

    def _on_console(self, message) -> None:
        self._console_events.append(
            self._redactor.redact({"type": message.type, "text": message.text})
        )
        if len(self._console_events) > 200:
            del self._console_events[:-200]

    @staticmethod
    def _sha(data: bytes | str) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def snapshot(self) -> BrowserSnapshot:
        page = self.page
        dom = page.content()
        png = page.screenshot(full_page=True)
        revision = self._sha(json.dumps({"url": page.url, "dom": self._sha(dom)}, sort_keys=True))
        return BrowserSnapshot(
            url=page.url,
            revision=revision,
            dom_digest=self._sha(dom),
            screenshot_digest=self._sha(png),
            title=page.title(),
            metadata={
                "network_event_count": len(self._network_events),
                "console_event_count": len(self._console_events),
                "security_event_count": len(self._security_events),
                "adapter": "playwright-owned-context",
            },
        )

    def _locator(self, spec: dict[str, Any]):
        if not isinstance(spec, dict):
            raise ValueError("locator must be an object")
        page = self.page
        if "role" in spec:
            return page.get_by_role(str(spec["role"]), name=spec.get("name"), exact=bool(spec.get("exact", True)))
        if "label" in spec:
            return page.get_by_label(str(spec["label"]), exact=bool(spec.get("exact", True)))
        if "test_id" in spec:
            return page.get_by_test_id(str(spec["test_id"]))
        if "text" in spec:
            return page.get_by_text(str(spec["text"]), exact=bool(spec.get("exact", True)))
        if "placeholder" in spec:
            return page.get_by_placeholder(str(spec["placeholder"]), exact=bool(spec.get("exact", True)))
        if "css" in spec and self.allow_css_locators:
            return page.locator(str(spec["css"]))
        raise ValueError("locator must use role, label, test_id, text, or placeholder")

    def _dom_postcondition(self, expected: dict[str, Any]) -> tuple[bool, list[str]]:
        notes: list[str] = []
        page = self.page
        ok = True
        if "url" in expected and page.url != expected["url"]:
            ok = False
            notes.append("url mismatch")
        if "url_contains" in expected and str(expected["url_contains"]) not in page.url:
            ok = False
            notes.append("url substring missing")
        if "visible" in expected:
            try:
                if not self._locator(dict(expected["visible"])).is_visible():
                    ok = False
                    notes.append("expected locator not visible")
            except Exception as exc:  # noqa: BLE001
                ok = False
                notes.append(f"visible assertion error: {type(exc).__name__}")
        if "text_contains" in expected:
            body = page.locator("body").inner_text()
            if str(expected["text_contains"]) not in body:
                ok = False
                notes.append("expected text missing")
        if "value_equals" in expected:
            spec = dict(expected["value_equals"])
            expected_value = str(spec.pop("value"))
            actual = self._locator(spec).input_value()
            if actual != expected_value:
                ok = False
                notes.append("input value mismatch")
        return ok, notes

    def _pixel_postcondition(
        self,
        expected: dict[str, Any],
        before: BrowserSnapshot,
        after: BrowserSnapshot,
    ) -> tuple[bool, list[str]]:
        mode = expected.get("pixel_assertion")
        if not mode:
            return False, ["no explicit pixel assertion"]
        if mode == "changed":
            return before.screenshot_digest != after.screenshot_digest, ["pixel digest change asserted"]
        if mode == "unchanged":
            return before.screenshot_digest == after.screenshot_digest, ["pixel digest stability asserted"]
        if mode == "sha256":
            wanted = str(expected.get("screenshot_sha256", ""))
            return after.screenshot_digest == wanted, ["exact screenshot digest asserted"]
        if mode == "capture_only":
            return bool(after.screenshot_digest), ["capture-only is weak evidence"]
        return False, ["unknown pixel assertion mode"]

    def _network_postcondition(self, expected: dict[str, Any], start_index: int) -> tuple[bool, list[str], str | None]:
        events = self._network_events[start_index:]
        rule = expected.get("network")
        if not rule:
            return False, ["no explicit network assertion"], None
        url_contains = str(rule.get("url_contains", ""))
        method = str(rule.get("method", "")).upper()
        statuses = {int(v) for v in rule.get("statuses", [200, 201, 202, 204])}
        matches = [
            event
            for event in events
            if (not url_contains or url_contains in str(event["url"]))
            and (not method or method == str(event["method"]).upper())
            and int(event["status"]) in statuses
        ]
        receipt = None
        if matches:
            receipt = self._sha(json.dumps(matches[-1], sort_keys=True))
        return bool(matches), [f"network matches: {len(matches)}"], receipt

    def execute(self, request: ActionRequest) -> ExecutionResult:
        page = self.page
        self._raise_security_violation()
        before = self.snapshot()
        network_start = len(self._network_events)
        rollback_token: dict[str, Any] | None = None
        payload = request.payload
        action = request.action_type
        output: dict[str, Any] = {}

        if action == "navigate":
            rollback_token = {"kind": "navigate", "url": before.url}
            try:
                response = page.goto(
                    request.target_url,
                    wait_until=str(payload.get("wait_until", "domcontentloaded")),
                    timeout=int(payload.get("timeout_ms", self.timeout_ms)),
                )
            except Exception:
                self._raise_security_violation()
                raise
            output["status"] = response.status if response else None
        elif action in {"inspect", "screenshot", "read_network", "read_console", "health", "wait"}:
            if action == "wait":
                page.wait_for_timeout(int(payload.get("milliseconds", 250)))
        elif action == "query":
            locator = self._locator(dict(payload["locator"]))
            output["text"] = self._redactor.redact(locator.inner_text())
        elif action == "type":
            locator_spec = dict(payload["locator"])
            locator = self._locator(locator_spec)
            prior = locator.input_value()
            rollback_token = {"kind": "fill", "locator": locator_spec, "value": prior}
            locator.fill(str(payload.get("value", "")))
        elif action == "select":
            locator_spec = dict(payload["locator"])
            locator = self._locator(locator_spec)
            prior = locator.input_value()
            rollback_token = {"kind": "select", "locator": locator_spec, "value": prior}
            locator.select_option(str(payload["value"]))
        elif action == "upload_staged":
            locator = self._locator(dict(payload["locator"]))
            file_path = Path(str(payload["file_path"])).resolve()
            allowed_root = Path(str(payload["allowed_root"])).resolve()
            if allowed_root not in file_path.parents:
                raise ValueError("upload file is outside the explicit allowed root")
            if not file_path.is_file():
                raise FileNotFoundError(file_path)
            output["file_sha256"] = self._sha(file_path.read_bytes())
            locator.set_input_files(str(file_path))
        elif action == "download":
            with page.expect_download(timeout=int(payload.get("timeout_ms", self.timeout_ms))) as info:
                self._locator(dict(payload["locator"])).click()
            download = info.value
            suggested = Path(download.suggested_filename).name
            destination = self.artifacts_dir / suggested
            download.save_as(str(destination))
            output.update(
                {
                    "path": str(destination),
                    "sha256": self._sha(destination.read_bytes()),
                    "size": destination.stat().st_size,
                }
            )
        elif action in {
            "create_draft",
            "edit_draft",
            "add_to_cart",
            "submit",
            "send",
            "publish",
            "comment",
            "book",
            "reserve",
            "start_paid_generation",
            "commit_upload",
            "create_external_resource",
        }:
            # Semantic action names carry the risk classification. The physical click
            # is allowed only through an explicit locator bound into the approved digest.
            self._locator(dict(payload["locator"])).click()
        else:
            raise ValueError(f"Adapter action is not implemented: {action}")

        if payload.get("wait_for"):
            self._locator(dict(payload["wait_for"])).wait_for(state="visible")

        self._raise_security_violation()
        after = self.snapshot()
        dom_ok, dom_notes = self._dom_postcondition(request.expected)
        pixel_ok, pixel_notes = self._pixel_postcondition(request.expected, before, after)
        network_ok, network_notes, provider_receipt = self._network_postcondition(
            request.expected, network_start
        )
        return ExecutionResult(
            before=before,
            after=after,
            signals=SignalBundle(
                dom_ok=dom_ok,
                pixel_ok=pixel_ok,
                network_ok=network_ok,
                provider_receipt=provider_receipt,
                notes=dom_notes + pixel_notes + network_notes,
            ),
            output=self._redactor.redact(output),
            rollback_token=rollback_token,
        )

    def rollback(self, rollback_token: dict[str, Any]) -> bool:
        kind = rollback_token.get("kind")
        if kind == "navigate":
            self.page.goto(str(rollback_token["url"]), wait_until="domcontentloaded")
            return True
        if kind == "fill":
            self._locator(dict(rollback_token["locator"])).fill(str(rollback_token["value"]))
            return True
        if kind == "select":
            self._locator(dict(rollback_token["locator"])).select_option(str(rollback_token["value"]))
            return True
        return False

    def close(self) -> None:
        """Close every owned Playwright resource exactly once.

        Cleanup is deliberately idempotent and each layer is attempted even when a
        preceding close operation fails. This prevents an exception while stopping
        tracing or a browser context from leaving the Playwright driver thread/process
        alive after a test or worker shutdown.
        """
        context, browser, playwright = self._context, self._browser, self._playwright
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
        trace_started = self._trace_started
        self._trace_started = False

        if context is not None and trace_started:
            try:
                self.trace_path.parent.mkdir(parents=True, exist_ok=True)
                context.tracing.stop(path=str(self.trace_path))
            except Exception:  # noqa: BLE001 - best-effort artifact close path
                pass
        if context is not None:
            try:
                context.close()
            except Exception:  # noqa: BLE001 - continue closing remaining owners
                pass
        if browser is not None:
            try:
                browser.close()
            except Exception:  # noqa: BLE001 - continue closing remaining owners
                pass
        if playwright is not None:
            try:
                playwright.stop()
            except Exception:  # noqa: BLE001 - shutdown must remain idempotent
                pass
