from __future__ import annotations

import tempfile
import unittest

from wbcp.errors import FailureCode
from wbcp.playwright_adapter import PlaywrightBrowserAdapter, PlaywrightUnavailable
from wbcp.url_guard import URLGuard, URLPolicy


class PlaywrightAdapterContractTests(unittest.TestCase):
    def test_live_adapter_fails_closed_when_dependency_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            adapter = PlaywrightBrowserAdapter(artifacts_dir=td)
            try:
                adapter.start()
            except PlaywrightUnavailable:
                return
            else:
                # If Playwright happens to be installed in the environment, close it.
                adapter.close()

    def test_css_locators_are_disabled_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            adapter = PlaywrightBrowserAdapter(artifacts_dir=td)
            self.assertFalse(adapter.allow_css_locators)

    def test_live_egress_without_url_guard_is_blocked(self) -> None:
        class Route:
            aborted = False
            continued = False

            def abort(self, *_args) -> None:
                self.aborted = True

            def continue_(self) -> None:
                self.continued = True

        class Request:
            url = "https://example.com/"
            redirected_from = None

        with tempfile.TemporaryDirectory() as td:
            adapter = PlaywrightBrowserAdapter(artifacts_dir=td)
            route = Route()
            adapter._route_request(route, Request())
            self.assertTrue(route.aborted)
            self.assertFalse(route.continued)
            self.assertEqual(adapter._security_violation.code, FailureCode.BLOCKED_UNSAFE_URL)

    def test_close_is_idempotent_and_stops_every_owner_after_cleanup_errors(self) -> None:
        class Tracing:
            def __init__(self) -> None:
                self.stop_count = 0

            def stop(self, *, path: str) -> None:
                self.stop_count += 1
                self.path = path
                raise RuntimeError("synthetic trace close failure")

        class Context:
            def __init__(self) -> None:
                self.tracing = Tracing()
                self.close_count = 0

            def close(self) -> None:
                self.close_count += 1
                raise RuntimeError("synthetic context close failure")

        class Browser:
            def __init__(self) -> None:
                self.close_count = 0

            def close(self) -> None:
                self.close_count += 1
                raise RuntimeError("synthetic browser close failure")

        class Playwright:
            def __init__(self) -> None:
                self.stop_count = 0

            def stop(self) -> None:
                self.stop_count += 1

        with tempfile.TemporaryDirectory() as td:
            adapter = PlaywrightBrowserAdapter(artifacts_dir=td)
            context = Context()
            browser = Browser()
            playwright = Playwright()
            adapter._context = context  # noqa: SLF001 - lifecycle regression fixture
            adapter._browser = browser  # noqa: SLF001 - lifecycle regression fixture
            adapter._playwright = playwright  # noqa: SLF001 - lifecycle regression fixture
            adapter._page = object()  # noqa: SLF001 - lifecycle regression fixture
            adapter._trace_started = True  # noqa: SLF001 - lifecycle regression fixture

            adapter.close()
            adapter.close()

            self.assertEqual(context.tracing.stop_count, 1)
            self.assertEqual(context.close_count, 1)
            self.assertEqual(browser.close_count, 1)
            self.assertEqual(playwright.stop_count, 1)
            self.assertIsNone(adapter._page)  # noqa: SLF001
            self.assertIsNone(adapter._context)  # noqa: SLF001
            self.assertIsNone(adapter._browser)  # noqa: SLF001
            self.assertIsNone(adapter._playwright)  # noqa: SLF001
            self.assertFalse(adapter._trace_started)  # noqa: SLF001

    def test_redirect_escape_is_recorded_with_exact_failure_code(self) -> None:
        class Route:
            aborted = False
            continued = False

            def abort(self, *_args) -> None:
                self.aborted = True

            def continue_(self) -> None:
                self.continued = True

        class Prior:
            url = "https://example.com/start"

        class Request:
            url = "https://evil.example.net/steal"
            redirected_from = Prior()

        with tempfile.TemporaryDirectory() as td:
            adapter = PlaywrightBrowserAdapter(
                artifacts_dir=td,
                url_guard=URLGuard(URLPolicy(allowed_hosts={"example.com"})),
            )
            route = Route()
            adapter._route_request(route, Request())
            self.assertTrue(route.aborted)
            self.assertEqual(
                adapter._security_violation.code, FailureCode.BLOCKED_REDIRECT_SCOPE_ESCAPE
            )


if __name__ == "__main__":
    unittest.main()
