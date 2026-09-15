from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path


STATIC = Path(__file__).parents[1] / "src" / "yue2_music_os" / "static"


class IdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.scripts: list[dict[str, str | None]] = []
        self.links: list[dict[str, str | None]] = []
        self.images: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "script":
            self.scripts.append(values)
        if tag == "link":
            self.links.append(values)
        if tag == "img":
            self.images.append(values)


def test_frontend_ids_match_javascript_contract() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    parser = IdCollector()
    parser.feed(html)
    referenced = set(re.findall(r"\$\('([^']+)'\)", js))
    missing = referenced - parser.ids
    assert not missing, f"JavaScript references missing HTML ids: {sorted(missing)}"


def test_frontend_uses_only_local_assets_and_no_inline_script() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    parser = IdCollector()
    parser.feed(html)
    assert parser.scripts
    assert all(item.get("src", "").startswith("/") for item in parser.scripts)
    assert all(item.get("href", "").startswith("/") for item in parser.links)
    assert all(item.get("src", "").startswith("/") for item in parser.images)
    for asset in [*parser.scripts, *parser.links, *parser.images]:
        reference = asset.get("src") or asset.get("href")
        assert reference is not None
        assert (STATIC / reference.lstrip("/")).is_file(), reference
    assert "http://" not in html and "https://" not in html
