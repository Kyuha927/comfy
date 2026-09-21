from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from .errors import ControlPlaneError
from .redaction import Redactor
from .runtime import BrowserControlRuntime


JSONRPC_VERSION = "2.0"
LATEST_PROTOCOL_VERSION = "2026-07-28"
SUPPORTED_PROTOCOL_VERSIONS = frozenset(
    {LATEST_PROTOCOL_VERSION, "2025-11-25", "2025-06-18", "2025-03-26"}
)


@dataclass(slots=True)
class RpcError(Exception):
    code: int
    message: str
    data: Any = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            value["data"] = self.data
        return value


@dataclass(frozen=True, slots=True)
class AccessContext:
    principal_id: str
    allowed_tools: frozenset[str] | None = None

    def permits(self, tool_name: str) -> bool:
        return self.allowed_tools is None or tool_name in self.allowed_tools


def _schema(
    *,
    properties: dict[str, Any] | None = None,
    required: list[str] | None = None,
    additional: bool = False,
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties or {},
        "required": required or [],
        "additionalProperties": additional,
    }


_STR = {"type": "string", "minLength": 1}
_OBJ = {"type": "object"}
_BOOL = {"type": "boolean"}
_NUM = {"type": "number", "minimum": 0}


def tool_catalog() -> list[dict[str, Any]]:
    action_common = {
        "sessionId": _STR,
        "idempotencyKey": _STR,
        "targetUrl": _STR,
        "engine": {"type": "string", "enum": ["AUTO", "PLAYWRIGHT", "JEV", "CUA"]},
        "payload": _OBJ,
        "expected": _OBJ,
        "authoritySource": {
            "type": "string",
            "enum": ["USER", "POLICY", "MODEL_PROPOSAL", "WEB_CONTENT"],
        },
        "pageRevision": {"type": ["string", "null"]},
        "estimatedCost": {"type": ["number", "null"], "minimum": 0},
        "currency": {"type": ["string", "null"]},
        "reversible": _BOOL,
        "permitToken": _STR,
        "approvalToken": _STR,
        "commit": _BOOL,
    }
    return [
        {
            "name": "browser.health",
            "description": "Read fail-closed readiness, evidence integrity, and active session count.",
            "inputSchema": _schema(),
            "annotations": {"readOnlyHint": True, "destructiveHint": False},
        },
        {
            "name": "browser.session.create",
            "description": "Create one isolated browser session after consuming an exact finite session permit.",
            "inputSchema": _schema(
                properties={
                    "sessionId": _STR,
                    "initialUrl": _STR,
                    "permitToken": _STR,
                    "idempotencyKey": _STR,
                },
                required=["sessionId", "initialUrl", "permitToken", "idempotencyKey"],
            ),
            "annotations": {"readOnlyHint": False, "destructiveHint": False},
        },
        {
            "name": "browser.session.close",
            "description": "Close one isolated browser session after consuming a finite permit.",
            "inputSchema": _schema(
                properties={
                    "sessionId": _STR,
                    "permitToken": _STR,
                    "idempotencyKey": _STR,
                },
                required=["sessionId", "permitToken", "idempotencyKey"],
            ),
            "annotations": {"readOnlyHint": False, "destructiveHint": False},
        },
        {
            "name": "browser.inspect",
            "description": "Preflight a durable read-only browser inspection. Optional finite permit can authorize and commit it.",
            "inputSchema": _schema(
                properties=action_common,
                required=["sessionId", "idempotencyKey"],
            ),
            "annotations": {"readOnlyHint": True, "destructiveHint": False},
        },
        {
            "name": "browser.navigate",
            "description": "Preflight a bounded navigation to an exact allowlisted HTTPS URL.",
            "inputSchema": _schema(
                properties=action_common,
                required=["sessionId", "idempotencyKey", "targetUrl"],
            ),
            "annotations": {"readOnlyHint": False, "destructiveHint": False},
        },
        {
            "name": "browser.query",
            "description": "Preflight a semantic-locator browser query without exposing arbitrary script execution.",
            "inputSchema": _schema(
                properties=action_common,
                required=["sessionId", "idempotencyKey", "payload"],
            ),
            "annotations": {"readOnlyHint": True, "destructiveHint": False},
        },
        {
            "name": "browser.action.preflight",
            "description": "Classify, normalize, digest, and durably record one typed action. This does not execute it.",
            "inputSchema": _schema(
                properties={**action_common, "actionType": _STR},
                required=["sessionId", "idempotencyKey", "actionType", "targetUrl"],
            ),
            "annotations": {"readOnlyHint": True, "destructiveHint": False},
        },
        {
            "name": "browser.action.authorize",
            "description": "Atomically consume a finite permit and any required one-shot approval for an exact action digest.",
            "inputSchema": _schema(
                properties={
                    "jobId": _STR,
                    "permitToken": _STR,
                    "approvalToken": _STR,
                },
                required=["jobId", "permitToken"],
            ),
            "annotations": {"readOnlyHint": False, "destructiveHint": False},
        },
        {
            "name": "browser.action.commit",
            "description": "Execute only an already-authorized durable job in its bound browser session and verify postconditions.",
            "inputSchema": _schema(
                properties={"jobId": _STR, "sessionId": _STR},
                required=["jobId", "sessionId"],
            ),
            "annotations": {"readOnlyHint": False, "destructiveHint": True},
        },
        {
            "name": "browser.job.get",
            "description": "Read one job after consuming an exact finite read permit.",
            "inputSchema": _schema(
                properties={
                    "jobId": _STR,
                    "permitToken": _STR,
                    "idempotencyKey": _STR,
                },
                required=["jobId", "permitToken", "idempotencyKey"],
            ),
            "annotations": {"readOnlyHint": True, "destructiveHint": False},
        },
        {
            "name": "browser.job.cancel",
            "description": "Cancel one nonterminal durable job after consuming an exact finite permit.",
            "inputSchema": _schema(
                properties={
                    "jobId": _STR,
                    "permitToken": _STR,
                    "idempotencyKey": _STR,
                },
                required=["jobId", "permitToken", "idempotencyKey"],
            ),
            "annotations": {"readOnlyHint": False, "destructiveHint": False},
        },
        {
            "name": "browser.evidence.get",
            "description": "Read redacted, hash-chained evidence for one job after consuming a finite read permit.",
            "inputSchema": _schema(
                properties={
                    "jobId": _STR,
                    "permitToken": _STR,
                    "idempotencyKey": _STR,
                    "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                },
                required=["jobId", "permitToken", "idempotencyKey"],
            ),
            "annotations": {"readOnlyHint": True, "destructiveHint": False},
        },
    ]


class McpProtocolServer:
    def __init__(self, runtime: BrowserControlRuntime) -> None:
        self.runtime = runtime
        self.redactor = Redactor()
        self._tools = {tool["name"]: tool for tool in tool_catalog()}
        self._handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "browser.health": lambda _: runtime.health(),
            "browser.session.create": runtime.create_session,
            "browser.session.close": runtime.close_session,
            "browser.inspect": lambda args: runtime.preflight(args, forced_action="inspect"),
            "browser.navigate": lambda args: runtime.preflight(args, forced_action="navigate"),
            "browser.query": lambda args: runtime.preflight(args, forced_action="query"),
            "browser.action.preflight": runtime.preflight,
            "browser.action.authorize": runtime.authorize,
            "browser.action.commit": runtime.commit,
            "browser.job.get": runtime.get_job,
            "browser.job.cancel": runtime.cancel_job,
            "browser.evidence.get": runtime.get_evidence,
        }

    @staticmethod
    def _validate_tool_arguments(schema: dict[str, Any], arguments: Any) -> dict[str, Any]:
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise RpcError(-32602, "Tool arguments must be an object")
        try:
            from jsonschema import Draft202012Validator
        except ImportError as exc:
            raise RpcError(-32603, "jsonschema dependency is required for tool validation") from exc
        errors = sorted(Draft202012Validator(schema).iter_errors(arguments), key=lambda e: list(e.path))
        if errors:
            formatted = [
                {"path": "/".join(str(part) for part in error.path), "message": error.message}
                for error in errors[:10]
            ]
            raise RpcError(-32602, "Invalid tool arguments", formatted)
        return dict(arguments)

    @staticmethod
    def _result_payload(value: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(value, sort_keys=True, ensure_ascii=False),
                }
            ],
            "structuredContent": value,
            "isError": is_error,
        }

    def call_tool(
        self,
        name: str,
        arguments: Any,
        *,
        access_context: AccessContext | None = None,
    ) -> dict[str, Any]:
        if access_context is not None and not access_context.permits(name):
            return self._result_payload(
                {
                    "error": {
                        "code": "BLOCKED_TRANSPORT_TOOL_NOT_ALLOWED",
                        "message": "The authenticated transport principal is not allowed to call this tool",
                        "principal_id": access_context.principal_id,
                        "tool": name,
                    }
                },
                is_error=True,
            )
        tool = self._tools.get(name)
        handler = self._handlers.get(name)
        if tool is None or handler is None:
            raise RpcError(-32602, "Unknown tool", {"name": name})
        validated = self._validate_tool_arguments(tool["inputSchema"], arguments)
        try:
            return self._result_payload(handler(validated))
        except ControlPlaneError as exc:
            return self._result_payload({"error": self.redactor.redact(exc.to_dict())}, is_error=True)
        except (KeyError, ValueError, TypeError) as exc:
            return self._result_payload(
                {
                    "error": {
                        "code": "BLOCKED_INVALID_TOOL_ARGUMENTS",
                        "message": str(exc),
                    }
                },
                is_error=True,
            )

    def _dispatch_method(
        self,
        method: str,
        params: Any,
        protocol_version: str,
        access_context: AccessContext | None,
    ) -> Any:
        if method == "ping":
            return {}
        if method == "initialize":
            requested = str((params or {}).get("protocolVersion", "2025-11-25"))
            chosen = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else "2025-11-25"
            return {
                "protocolVersion": chosen,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "wbcp", "version": self.runtime.VERSION},
                "instructions": "All browser mutations require preflight, finite authorization, commit, and independent postcondition evidence.",
            }
        if method in {"notifications/initialized", "notifications/cancelled"}:
            return None
        if method == "server/discover":
            return {
                "protocolVersion": LATEST_PROTOCOL_VERSION,
                "serverInfo": {"name": "wbcp", "version": self.runtime.VERSION},
                "capabilities": {"tools": {"listChanged": False}},
                "tools": [
                    tool
                    for name, tool in self._tools.items()
                    if access_context is None or access_context.permits(name)
                ],
            }
        if method == "tools/list":
            return {
                "tools": [
                    tool
                    for name, tool in self._tools.items()
                    if access_context is None or access_context.permits(name)
                ]
            }
        if method == "tools/call":
            if not isinstance(params, dict):
                raise RpcError(-32602, "tools/call params must be an object")
            name = str(params.get("name", ""))
            return self.call_tool(
                name,
                params.get("arguments", {}),
                access_context=access_context,
            )
        raise RpcError(-32601, "Method not found", {"method": method})

    def handle_message(
        self,
        message: Any,
        *,
        protocol_version: str = LATEST_PROTOCOL_VERSION,
        header_method: str | None = None,
        header_name: str | None = None,
        access_context: AccessContext | None = None,
    ) -> dict[str, Any] | None:
        if not isinstance(message, dict):
            raise RpcError(-32600, "JSON-RPC request must be an object")
        if message.get("jsonrpc") != JSONRPC_VERSION:
            raise RpcError(-32600, "jsonrpc must be 2.0")
        method = message.get("method")
        if not isinstance(method, str) or not method:
            raise RpcError(-32600, "method is required")
        if header_method and header_method != method:
            raise RpcError(-32600, "Mcp-Method header does not match JSON-RPC method")
        params = message.get("params", {})
        if header_name and method == "tools/call":
            body_name = str(params.get("name", "")) if isinstance(params, dict) else ""
            if header_name != body_name:
                raise RpcError(-32600, "Mcp-Name header does not match tool name")
        request_id = message.get("id")
        is_notification = "id" not in message
        try:
            result = self._dispatch_method(
                method, params, protocol_version, access_context
            )
            if is_notification:
                return None
            return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}
        except RpcError:
            raise
        except Exception as exc:  # noqa: BLE001 - RPC boundary
            raise RpcError(-32603, "Internal error", {"type": type(exc).__name__}) from exc

    @staticmethod
    def error_response(request_id: Any, error: RpcError) -> dict[str, Any]:
        return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "error": error.to_dict()}
