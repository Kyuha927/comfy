from __future__ import annotations

import unittest

from wbcp.errors import ControlPlaneError, FailureCode
from wbcp.url_guard import URLGuard, URLPolicy


class URLGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guard = URLGuard(
            URLPolicy(allowed_hosts={"example.com", "*.safe.example"}, allowed_ports={443})
        )

    def assertBlocked(self, url: str, code: FailureCode) -> None:  # noqa: N802
        with self.assertRaises(ControlPlaneError) as ctx:
            self.guard.validate(url)
        self.assertEqual(ctx.exception.code, code)

    def test_allows_exact_https_host(self) -> None:
        result = self.guard.validate("https://example.com/path?q=1#ignored")
        self.assertEqual(result.normalized, "https://example.com/path?q=1")
        self.assertEqual(result.port, 443)

    def test_allows_wildcard_subdomain_but_not_root(self) -> None:
        self.assertEqual(self.guard.validate("https://a.safe.example/").host, "a.safe.example")
        self.assertBlocked("https://safe.example/", FailureCode.BLOCKED_DOMAIN_NOT_ALLOWED)

    def test_blocks_plain_http(self) -> None:
        self.assertBlocked("http://example.com/", FailureCode.BLOCKED_UNSAFE_URL)

    def test_blocks_dangerous_schemes(self) -> None:
        for url in ("file:///etc/passwd", "javascript:alert(1)", "data:text/plain,x"):
            with self.subTest(url=url):
                self.assertBlocked(url, FailureCode.BLOCKED_UNSAFE_URL)

    def test_blocks_credentials_in_url(self) -> None:
        self.assertBlocked(
            "https://user:pass@example.com/", FailureCode.BLOCKED_SECRET_EXPOSURE_RISK
        )

    def test_blocks_private_and_loopback_literals(self) -> None:
        for url in (
            "https://127.0.0.1/",
            "https://10.0.0.1/",
            "https://169.254.169.254/",
            "https://[::1]/",
        ):
            with self.subTest(url=url):
                self.assertBlocked(url, FailureCode.BLOCKED_SSRF_TARGET)

    def test_blocks_internal_suffix(self) -> None:
        guard = URLGuard(URLPolicy(allowed_hosts={"admin.internal"}))
        with self.assertRaises(ControlPlaneError) as ctx:
            guard.validate("https://admin.internal/")
        self.assertEqual(ctx.exception.code, FailureCode.BLOCKED_SSRF_TARGET)

    def test_blocks_non_allowed_port(self) -> None:
        self.assertBlocked("https://example.com:8443/", FailureCode.BLOCKED_UNSAFE_URL)

    def test_blocks_control_char_even_percent_encoded(self) -> None:
        self.assertBlocked("https://example.com/%0aevil", FailureCode.BLOCKED_UNSAFE_URL)

    def test_redirect_escape_gets_specific_code(self) -> None:
        with self.assertRaises(ControlPlaneError) as ctx:
            self.guard.validate_redirect_chain(
                ["https://example.com/start", "https://evil.example.net/steal"]
            )
        self.assertEqual(ctx.exception.code, FailureCode.BLOCKED_REDIRECT_SCOPE_ESCAPE)

    def test_resolved_ip_must_be_global(self) -> None:
        with self.assertRaises(ControlPlaneError) as ctx:
            URLGuard.validate_resolved_ips(["192.168.1.20"])
        self.assertEqual(ctx.exception.code, FailureCode.BLOCKED_SSRF_TARGET)
        URLGuard.validate_resolved_ips(["8.8.8.8"])


if __name__ == "__main__":
    unittest.main()
