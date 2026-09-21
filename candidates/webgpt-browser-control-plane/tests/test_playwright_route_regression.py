from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from wbcp.playwright_adapter import PlaywrightBrowserAdapter
from wbcp.url_guard import URLGuard, URLPolicy


class _Route:
    def __init__(self) -> None:
        self.continue_count = 0
        self.abort_count = 0

    def continue_(self) -> None:
        self.continue_count += 1

    def abort(self, _: str) -> None:
        self.abort_count += 1


class _Request:
    url = "https://example.com/app.js"
    redirected_from = None


class PlaywrightRouteRegressionTests(unittest.TestCase):
    def test_allowed_route_is_continued_exactly_once(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            adapter = PlaywrightBrowserAdapter(
                artifacts_dir=Path(td),
                url_guard=URLGuard(URLPolicy(allowed_hosts={"example.com"})),
            )
            route = _Route()
            adapter._route_request(route, _Request())  # noqa: SLF001 - discriminating regression
            self.assertEqual(route.continue_count, 1)
            self.assertEqual(route.abort_count, 0)


if __name__ == "__main__":
    unittest.main()
