from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .models import ActionRequest, BrowserSnapshot, ExecutionResult, SignalBundle


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


@dataclass
class MockBrowserState:
    url: str = "https://example.com/"
    revision_number: int = 0
    title: str = "Example"
    fields: dict[str, Any] = field(default_factory=dict)
    selected: dict[str, Any] = field(default_factory=dict)
    drafts: dict[str, Any] = field(default_factory=dict)
    cart: list[Any] = field(default_factory=list)
    submitted: bool = False
    published: bool = False
    resource_created: bool = False
    text: str = "ready"


class MockBrowserAdapter:
    """Deterministic browser simulator used only for offline acceptance tests."""

    def __init__(self, initial_url: str = "https://example.com/") -> None:
        self.state = MockBrowserState(url=initial_url)
        self.fail_rollback = False

    def open_initial_url(self, url: str) -> BrowserSnapshot:
        self.state.url = url
        return self.snapshot()

    def snapshot(self) -> BrowserSnapshot:
        visible = {
            "url": self.state.url,
            "title": self.state.title,
            "fields": self.state.fields,
            "selected": self.state.selected,
            "drafts": self.state.drafts,
            "cart": self.state.cart,
            "submitted": self.state.submitted,
            "published": self.state.published,
            "resource_created": self.state.resource_created,
            "text": self.state.text,
        }
        return BrowserSnapshot(
            url=self.state.url,
            revision=f"rev-{self.state.revision_number}",
            dom_digest=_digest(visible),
            screenshot_digest=_digest({"pixels": visible}),
            title=self.state.title,
            metadata={"simulator": True},
        )

    def _postcondition_dom_ok(self, request: ActionRequest) -> bool:
        expected = request.expected
        if "url" in expected and self.state.url != expected["url"]:
            return False
        if "url_contains" in expected and str(expected["url_contains"]) not in self.state.url:
            return False
        if "field_equals" in expected:
            for key, value in dict(expected["field_equals"]).items():
                if self.state.fields.get(key) != value:
                    return False
        if "submitted" in expected and self.state.submitted is not bool(expected["submitted"]):
            return False
        if "published" in expected and self.state.published is not bool(expected["published"]):
            return False
        if "resource_created" in expected and self.state.resource_created is not bool(expected["resource_created"]):
            return False
        if "text_contains" in expected and str(expected["text_contains"]) not in self.state.text:
            return False
        return True

    def execute(self, request: ActionRequest) -> ExecutionResult:
        if request.payload.get("simulate_execution_failure"):
            raise RuntimeError("simulated browser execution failure")
        before_state = copy.deepcopy(self.state)
        before = self.snapshot()
        action = request.action_type
        payload = request.payload

        if action == "navigate":
            self.state.url = request.target_url
        elif action in {"inspect", "query", "screenshot", "read_network", "read_console", "health", "job_get", "evidence_get", "wait"}:
            pass
        elif action in {"scroll", "focus", "switch_tab", "open_tab", "close_tab"}:
            self.state.text = f"{action}:ok"
        elif action == "type":
            self.state.fields[str(payload.get("field", "field"))] = payload.get("value")
        elif action == "select":
            self.state.selected[str(payload.get("field", "field"))] = payload.get("value")
        elif action in {"create_draft", "edit_draft"}:
            self.state.drafts[str(payload.get("draft_id", "draft"))] = payload.get("content", {})
        elif action == "add_to_cart":
            self.state.cart.append(payload.get("item"))
        elif action in {"submit", "send", "book", "reserve", "commit_upload"}:
            self.state.submitted = True
        elif action in {"publish", "comment"}:
            self.state.published = True
        elif action in {"start_paid_generation", "create_external_resource"}:
            self.state.resource_created = True
        elif action in {"upload_staged", "download", "checkpoint"}:
            self.state.text = f"{action}:ok"
        else:
            self.state.text = f"{action}:executed"

        if action not in {"inspect", "query", "screenshot", "read_network", "read_console", "health", "job_get", "evidence_get", "wait"}:
            self.state.revision_number += 1
        after = self.snapshot()
        dom_ok = self._postcondition_dom_ok(request) and not bool(payload.get("simulate_dom_failure"))
        pixel_ok = not bool(payload.get("simulate_pixel_failure"))
        network_ok = not bool(payload.get("simulate_network_failure"))
        receipt = None
        if action in {"submit", "send", "publish", "comment", "book", "reserve", "start_paid_generation", "commit_upload", "create_external_resource"}:
            receipt = f"mock-provider-{request.idempotency_key}"
        return ExecutionResult(
            before=before,
            after=after,
            signals=SignalBundle(
                dom_ok=dom_ok,
                pixel_ok=pixel_ok,
                network_ok=network_ok,
                provider_receipt=receipt,
                notes=["offline mock adapter; not production browser evidence"],
            ),
            output={"action": action, "mock": True, "provider_receipt": receipt},
            rollback_token={"state": before_state},
        )

    def rollback(self, rollback_token: dict[str, Any]) -> bool:
        if self.fail_rollback:
            return False
        prior = rollback_token.get("state")
        if not isinstance(prior, MockBrowserState):
            return False
        restored = copy.deepcopy(prior)
        restored.revision_number = self.state.revision_number + 1
        self.state = restored
        return True
