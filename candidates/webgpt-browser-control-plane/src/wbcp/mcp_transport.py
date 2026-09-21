from __future__ import annotations

import hmac
import json
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from .errors import ControlPlaneError, FailureCode
from .mcp_protocol import (
    LATEST_PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    AccessContext,
    McpProtocolServer,
    RpcError,
)


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON object key: {key}")
        value[key] = item
    return value


@dataclass(frozen=True, slots=True)
class HttpTransportConfig:
    bearer_token: str
    allowed_origins: frozenset[str]
    allowed_hosts: frozenset[str]
    require_origin: bool = False
    max_request_bytes: int = 1_048_576
    max_batch_items: int = 32
    principal_id: str = "chatgpt-mcp-client"
    allowed_tools: frozenset[str] = frozenset()
    requests_per_minute: int = 120
    max_concurrent_requests: int = 8


class McpHttpTransport:
    def __init__(self, protocol: McpProtocolServer, config: HttpTransportConfig) -> None:
        if len(config.bearer_token) < 32:
            raise ValueError("HTTP bearer token must be at least 32 characters")
        if not config.allowed_hosts:
            raise ValueError("At least one HTTP Host allowlist entry is required")
        if config.max_request_bytes < 1_024:
            raise ValueError("HTTP request cap must be at least 1 KiB")
        if config.max_batch_items < 1 or config.max_batch_items > 256:
            raise ValueError("HTTP batch-item limit is outside safe range")
        if not config.principal_id.strip():
            raise ValueError("HTTP principal ID must be non-empty")
        if config.requests_per_minute < 1:
            raise ValueError("HTTP requests-per-minute limit must be positive")
        if config.max_concurrent_requests < 1:
            raise ValueError("HTTP concurrent-request limit must be positive")
        self.protocol = protocol
        self.config = config
        self._request_times: deque[float] = deque()
        self._rate_lock = threading.Lock()
        self._active_requests = 0
        self._capacity_lock = threading.Lock()

    @staticmethod
    def _host_only(value: str) -> str:
        value = value.strip().lower()
        if value.startswith("[") and "]" in value:
            return value[1 : value.index("]")]
        return value.split(":", 1)[0]

    def _response_headers(
        self,
        request,
        *,
        protocol_version: str | None = None,
        retry_after: str | None = None,
    ) -> dict[str, str]:
        headers = {"Cache-Control": "no-store"}
        if protocol_version:
            headers["MCP-Protocol-Version"] = protocol_version
        if retry_after:
            headers["Retry-After"] = retry_after
        origin = request.headers.get("origin")
        if origin and origin in self.config.allowed_origins:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Vary"] = "Origin"
        return headers

    def _consume_rate_budget(self) -> None:
        now = time.monotonic()
        cutoff = now - 60.0
        with self._rate_lock:
            while self._request_times and self._request_times[0] <= cutoff:
                self._request_times.popleft()
            if len(self._request_times) >= self.config.requests_per_minute:
                raise ControlPlaneError(
                    FailureCode.BLOCKED_TRANSPORT_RATE_LIMITED,
                    "Authenticated transport request rate exceeded",
                    {"window_seconds": 60},
                )
            self._request_times.append(now)

    def _enter_capacity(self) -> None:
        with self._capacity_lock:
            if self._active_requests >= self.config.max_concurrent_requests:
                raise ControlPlaneError(
                    FailureCode.BLOCKED_TRANSPORT_CAPACITY_EXHAUSTED,
                    "Transport concurrent-request capacity is exhausted",
                    {"max_concurrent_requests": self.config.max_concurrent_requests},
                )
            self._active_requests += 1

    def _leave_capacity(self) -> None:
        with self._capacity_lock:
            self._active_requests = max(0, self._active_requests - 1)

    def _authorize(self, request) -> AccessContext:
        host = self._host_only(request.headers.get("host", ""))
        if host not in self.config.allowed_hosts:
            raise ControlPlaneError(
                FailureCode.BLOCKED_TRANSPORT_HOST_NOT_ALLOWED,
                "HTTP Host is not allowlisted",
                {"host": host},
            )
        origin = request.headers.get("origin")
        if self.config.require_origin and not origin:
            raise ControlPlaneError(
                FailureCode.BLOCKED_TRANSPORT_ORIGIN_NOT_ALLOWED,
                "Origin header is required by transport policy",
            )
        if origin and origin not in self.config.allowed_origins:
            raise ControlPlaneError(
                FailureCode.BLOCKED_TRANSPORT_ORIGIN_NOT_ALLOWED,
                "Origin is not allowlisted",
                {"origin": origin},
            )
        auth = request.headers.get("authorization", "")
        prefix = "Bearer "
        supplied = auth[len(prefix) :] if auth.startswith(prefix) else ""
        if not hmac.compare_digest(supplied, self.config.bearer_token):
            raise ControlPlaneError(
                FailureCode.BLOCKED_TRANSPORT_AUTHENTICATION_FAILED,
                "Bearer authentication failed",
            )
        self._consume_rate_budget()
        return AccessContext(
            principal_id=self.config.principal_id,
            allowed_tools=self.config.allowed_tools or None,
        )

    @staticmethod
    def _protocol_version(request) -> str:
        return request.headers.get("mcp-protocol-version", LATEST_PROTOCOL_VERSION)

    async def _read_bounded_body(self, request) -> bytes:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.config.max_request_bytes:
            raise ControlPlaneError(
                FailureCode.BLOCKED_TRANSPORT_REQUEST_TOO_LARGE,
                "MCP request exceeds configured size cap",
            )
        chunks: list[bytes] = []
        total = 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > self.config.max_request_bytes:
                raise ControlPlaneError(
                    FailureCode.BLOCKED_TRANSPORT_REQUEST_TOO_LARGE,
                    "MCP request exceeds configured size cap",
                )
            chunks.append(chunk)
        return b"".join(chunks)

    def app(self):
        try:
            from starlette.applications import Starlette
            from starlette.requests import Request
            from starlette.responses import JSONResponse, Response
            from starlette.routing import Route
        except ImportError as exc:
            raise RuntimeError("Install the wbcp http extra to serve Streamable HTTP") from exc

        async def get_mcp(request: Request) -> Response:
            return Response(
                status_code=405,
                headers={"Allow": "POST", **self._response_headers(request)},
            )

        async def options_mcp(request: Request) -> Response:
            host = self._host_only(request.headers.get("host", ""))
            if host not in self.config.allowed_hosts:
                return JSONResponse(
                    {"error": FailureCode.BLOCKED_TRANSPORT_HOST_NOT_ALLOWED.value},
                    status_code=403,
                    headers=self._response_headers(request),
                )
            origin = request.headers.get("origin")
            if self.config.require_origin and not origin:
                return JSONResponse(
                    {"error": FailureCode.BLOCKED_TRANSPORT_ORIGIN_NOT_ALLOWED.value},
                    status_code=403,
                    headers=self._response_headers(request),
                )
            if origin and origin not in self.config.allowed_origins:
                return JSONResponse(
                    {"error": FailureCode.BLOCKED_TRANSPORT_ORIGIN_NOT_ALLOWED.value},
                    status_code=403,
                    headers=self._response_headers(request),
                )
            headers = {
                "Allow": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Authorization, Content-Type, MCP-Protocol-Version, Mcp-Method, Mcp-Name",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                **self._response_headers(request),
            }
            return Response(status_code=204, headers=headers)

        async def post_mcp(request: Request) -> Response:
            request_id: Any = None
            capacity_acquired = False
            version = self._protocol_version(request)
            try:
                access_context = self._authorize(request)
                self._enter_capacity()
                capacity_acquired = True
                if version not in SUPPORTED_PROTOCOL_VERSIONS:
                    raise ControlPlaneError(
                        FailureCode.BLOCKED_TRANSPORT_PROTOCOL_VERSION,
                        "Unsupported MCP protocol version",
                        {"protocol_version": version},
                    )
                content_type = (
                    request.headers.get("content-type", "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )
                if content_type != "application/json":
                    return JSONResponse(
                        {"error": "CONTENT_TYPE_MUST_BE_APPLICATION_JSON"},
                        status_code=415,
                        headers=self._response_headers(request, protocol_version=version),
                    )
                body = await self._read_bounded_body(request)
                try:
                    payload = json.loads(body, object_pairs_hook=_object_without_duplicate_keys)
                except (json.JSONDecodeError, UnicodeDecodeError, RecursionError, ValueError):
                    rpc = RpcError(-32700, "Parse error")
                    return JSONResponse(
                        McpProtocolServer.error_response(None, rpc),
                        status_code=400,
                        headers=self._response_headers(request, protocol_version=version),
                    )
                messages = payload if isinstance(payload, list) else [payload]
                if not messages:
                    rpc = RpcError(-32600, "Empty JSON-RPC batch is invalid")
                    return JSONResponse(
                        McpProtocolServer.error_response(None, rpc),
                        status_code=400,
                        headers=self._response_headers(request, protocol_version=version),
                    )
                if len(messages) > self.config.max_batch_items:
                    raise ControlPlaneError(
                        FailureCode.BLOCKED_TRANSPORT_BATCH_TOO_LARGE,
                        "MCP batch exceeds configured item cap",
                        {"max_batch_items": self.config.max_batch_items},
                    )
                responses: list[dict[str, Any]] = []
                for message in messages:
                    request_id = message.get("id") if isinstance(message, dict) else None
                    try:
                        result = self.protocol.handle_message(
                            message,
                            protocol_version=version,
                            header_method=request.headers.get("mcp-method"),
                            header_name=request.headers.get("mcp-name"),
                            access_context=access_context,
                        )
                        if result is not None:
                            responses.append(result)
                    except RpcError as exc:
                        responses.append(McpProtocolServer.error_response(request_id, exc))
                if not responses:
                    return Response(
                        status_code=202,
                        headers=self._response_headers(request, protocol_version=version),
                    )
                result_payload: Any = responses if isinstance(payload, list) else responses[0]
                return JSONResponse(
                    result_payload,
                    headers=self._response_headers(request, protocol_version=version),
                )
            except ControlPlaneError as exc:
                status = 403
                retry_after: str | None = None
                if exc.code == FailureCode.BLOCKED_TRANSPORT_AUTHENTICATION_FAILED:
                    status = 401
                elif exc.code == FailureCode.BLOCKED_TRANSPORT_PROTOCOL_VERSION:
                    status = 400
                elif exc.code in {
                    FailureCode.BLOCKED_TRANSPORT_REQUEST_TOO_LARGE,
                    FailureCode.BLOCKED_TRANSPORT_BATCH_TOO_LARGE,
                }:
                    status = 413
                elif exc.code == FailureCode.BLOCKED_TRANSPORT_RATE_LIMITED:
                    status = 429
                    retry_after = "60"
                elif exc.code == FailureCode.BLOCKED_TRANSPORT_CAPACITY_EXHAUSTED:
                    status = 503
                    retry_after = "1"
                return JSONResponse(
                    McpProtocolServer.error_response(
                        request_id,
                        RpcError(-32001, exc.message, exc.to_dict()),
                    ),
                    status_code=status,
                    headers=self._response_headers(
                        request,
                        protocol_version=version,
                        retry_after=retry_after,
                    ),
                )
            except (ValueError, TypeError):
                return JSONResponse(
                    McpProtocolServer.error_response(
                        request_id, RpcError(-32600, "Invalid request")
                    ),
                    status_code=400,
                    headers=self._response_headers(request, protocol_version=version),
                )
            finally:
                if capacity_acquired:
                    self._leave_capacity()

        return Starlette(
            routes=[
                Route("/mcp", get_mcp, methods=["GET"]),
                Route("/mcp", options_mcp, methods=["OPTIONS"]),
                Route("/mcp", post_mcp, methods=["POST"]),
            ]
        )


def run_stdio(protocol: McpProtocolServer, *, max_line_bytes: int = 1_048_576) -> int:
    """Serve newline-delimited JSON-RPC over stdio without writing logs to stdout."""

    for raw in sys.stdin.buffer:
        if len(raw) > max_line_bytes:
            response = McpProtocolServer.error_response(
                None, RpcError(-32600, "Request exceeds stdio size cap")
            )
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()
            continue
        try:
            message = json.loads(raw, object_pairs_hook=_object_without_duplicate_keys)
            request_id = message.get("id") if isinstance(message, dict) else None
            try:
                response = protocol.handle_message(message)
            except RpcError as exc:
                response = McpProtocolServer.error_response(request_id, exc)
        except (json.JSONDecodeError, UnicodeDecodeError, RecursionError, ValueError):
            response = McpProtocolServer.error_response(None, RpcError(-32700, "Parse error"))
        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":"), ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0
