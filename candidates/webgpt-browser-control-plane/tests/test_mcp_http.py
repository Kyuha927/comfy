from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from starlette.testclient import TestClient

from wbcp.mcp_protocol import McpProtocolServer
from wbcp.mcp_transport import HttpTransportConfig, McpHttpTransport
from wbcp.runtime import BrowserControlRuntime, build_runtime
from wbcp.settings import RuntimeSettings


class McpHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        settings = RuntimeSettings.for_tests(Path(self.tempdir.name))
        self.runtime = BrowserControlRuntime(build_runtime(settings))
        config = HttpTransportConfig(
            bearer_token="T" * 48,
            allowed_origins=frozenset({"https://chatgpt.com"}),
            allowed_hosts=frozenset({"testserver"}),
            max_request_bytes=2048,
        )
        self._client_context = TestClient(
            McpHttpTransport(McpProtocolServer(self.runtime), config).app()
        )
        self.client = self._client_context.__enter__()
        self.headers = {
            "Authorization": "Bearer " + "T" * 48,
            "Origin": "https://chatgpt.com",
            "MCP-Protocol-Version": "2026-07-28",
        }

    def tearDown(self) -> None:
        try:
            self._client_context.__exit__(None, None, None)
        finally:
            self.runtime.close()
            self.tempdir.cleanup()

    def test_get_is_not_a_hidden_event_stream(self) -> None:
        response = self.client.get("/mcp")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.headers["allow"], "POST")

    def test_missing_bearer_is_rejected(self) -> None:
        response = self.client.post(
            "/mcp",
            headers={"Origin": "https://chatgpt.com", "Content-Type": "application/json"},
            json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["error"]["data"]["code"],
            "BLOCKED_TRANSPORT_AUTHENTICATION_FAILED",
        )

    def test_origin_is_exactly_allowlisted(self) -> None:
        headers = dict(self.headers)
        headers["Origin"] = "https://evil.example"
        response = self.client.post(
            "/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": "ping"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["error"]["data"]["code"],
            "BLOCKED_TRANSPORT_ORIGIN_NOT_ALLOWED",
        )

    def test_host_header_is_exactly_allowlisted(self) -> None:
        headers = dict(self.headers)
        headers["Host"] = "evil.example"
        response = self.client.post(
            "/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": "ping"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["error"]["data"]["code"],
            "BLOCKED_TRANSPORT_HOST_NOT_ALLOWED",
        )

    def test_unsupported_protocol_version_fails_closed(self) -> None:
        headers = dict(self.headers)
        headers["MCP-Protocol-Version"] = "2099-01-01"
        response = self.client.post(
            "/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": "ping"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"]["data"]["code"],
            "BLOCKED_TRANSPORT_PROTOCOL_VERSION",
        )

    def test_ping_and_tools_list(self) -> None:
        ping = self.client.post(
            "/mcp", headers=self.headers, json={"jsonrpc": "2.0", "id": 1, "method": "ping"}
        )
        self.assertEqual(ping.status_code, 200)
        self.assertEqual(ping.json()["result"], {})
        tools = self.client.post(
            "/mcp",
            headers=self.headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        self.assertEqual(tools.status_code, 200)
        self.assertGreater(len(tools.json()["result"]["tools"]), 5)
        self.assertEqual(tools.headers["mcp-protocol-version"], "2026-07-28")

    def test_notification_returns_202_without_fabricated_result(self) -> None:
        response = self.client.post(
            "/mcp",
            headers=self.headers,
            json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.content, b"")

    def test_method_and_tool_name_headers_are_consistency_checks(self) -> None:
        headers = dict(self.headers)
        headers["Mcp-Method"] = "tools/call"
        headers["Mcp-Name"] = "browser.inspect"
        response = self.client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "browser.health", "arguments": {}},
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["error"]["code"], -32600)

    def test_request_size_cap_is_enforced_before_dispatch(self) -> None:
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "ping",
                "padding": "x" * 3000,
            }
        ).encode()
        headers = dict(self.headers)
        headers["Content-Type"] = "application/json"
        response = self.client.post("/mcp", headers=headers, content=body)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(
            response.json()["error"]["data"]["code"],
            "BLOCKED_TRANSPORT_REQUEST_TOO_LARGE",
        )

    def test_batch_request_preserves_independent_results(self) -> None:
        response = self.client.post(
            "/mcp",
            headers=self.headers,
            json=[
                {"jsonrpc": "2.0", "id": 1, "method": "ping"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            ],
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual([item["id"] for item in payload], [1, 2])

    def test_transport_tool_allowlist_filters_discovery_and_blocks_calls(self) -> None:
        config = HttpTransportConfig(
            bearer_token="T" * 48,
            allowed_origins=frozenset({"https://chatgpt.com"}),
            allowed_hosts=frozenset({"testserver"}),
            principal_id="readiness-probe",
            allowed_tools=frozenset({"browser.health"}),
        )
        with TestClient(McpHttpTransport(McpProtocolServer(self.runtime), config).app()) as client:
            tools = client.post(
                "/mcp",
                headers=self.headers,
                json={"jsonrpc": "2.0", "id": 21, "method": "tools/list", "params": {}},
            )
            self.assertEqual(tools.status_code, 200)
            self.assertEqual(
                [tool["name"] for tool in tools.json()["result"]["tools"]],
                ["browser.health"],
            )
            blocked = client.post(
                "/mcp",
                headers=self.headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 22,
                    "method": "tools/call",
                    "params": {
                        "name": "browser.inspect",
                        "arguments": {"sessionId": "s", "idempotencyKey": "i"},
                    },
                },
            )
            self.assertEqual(blocked.status_code, 200)
            result = blocked.json()["result"]
            self.assertTrue(result["isError"])
            self.assertEqual(
                result["structuredContent"]["error"]["code"],
                "BLOCKED_TRANSPORT_TOOL_NOT_ALLOWED",
            )
            self.assertEqual(
                result["structuredContent"]["error"]["principal_id"],
                "readiness-probe",
            )

    def test_authenticated_request_rate_limit_is_fail_closed(self) -> None:
        config = HttpTransportConfig(
            bearer_token="T" * 48,
            allowed_origins=frozenset({"https://chatgpt.com"}),
            allowed_hosts=frozenset({"testserver"}),
            requests_per_minute=1,
        )
        with TestClient(McpHttpTransport(McpProtocolServer(self.runtime), config).app()) as client:
            first = client.post(
                "/mcp",
                headers=self.headers,
                json={"jsonrpc": "2.0", "id": 31, "method": "ping"},
            )
            second = client.post(
                "/mcp",
                headers=self.headers,
                json={"jsonrpc": "2.0", "id": 32, "method": "ping"},
            )
            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 429)
            self.assertEqual(second.headers["retry-after"], "60")
            self.assertEqual(
                second.json()["error"]["data"]["code"],
                "BLOCKED_TRANSPORT_RATE_LIMITED",
            )

    def test_options_rejects_unallowlisted_host(self) -> None:
        response = self.client.options(
            "/mcp",
            headers={"Host": "evil.example", "Origin": "https://chatgpt.com"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["error"], "BLOCKED_TRANSPORT_HOST_NOT_ALLOWED"
        )

    def test_success_response_exposes_only_allowlisted_cors_origin(self) -> None:
        response = self.client.post(
            "/mcp",
            headers=self.headers,
            json={"jsonrpc": "2.0", "id": 41, "method": "ping"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"], "https://chatgpt.com"
        )
        self.assertEqual(response.headers["vary"], "Origin")

    def test_duplicate_json_object_keys_are_rejected(self) -> None:
        headers = dict(self.headers)
        headers["Content-Type"] = "application/json"
        response = self.client.post(
            "/mcp",
            headers=headers,
            content=b'{"jsonrpc":"2.0","id":1,"method":"ping","method":"tools/list"}',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], -32700)

    def test_batch_item_cap_is_enforced(self) -> None:
        config = HttpTransportConfig(
            bearer_token="T" * 48,
            allowed_origins=frozenset({"https://chatgpt.com"}),
            allowed_hosts=frozenset({"testserver"}),
            max_batch_items=2,
        )
        with TestClient(McpHttpTransport(McpProtocolServer(self.runtime), config).app()) as client:
            response = client.post(
                "/mcp",
                headers=self.headers,
                json=[
                    {"jsonrpc": "2.0", "id": 1, "method": "ping"},
                    {"jsonrpc": "2.0", "id": 2, "method": "ping"},
                    {"jsonrpc": "2.0", "id": 3, "method": "ping"},
                ],
            )
            self.assertEqual(response.status_code, 413)
            self.assertEqual(
                response.json()["error"]["data"]["code"],
                "BLOCKED_TRANSPORT_BATCH_TOO_LARGE",
            )


if __name__ == "__main__":
    unittest.main()
