from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def discover_chromium_executable() -> str | None:
    """Find an explicitly installed Chromium-family binary without launching it.

    The environment override is useful for a dedicated WBCP test browser.  On
    macOS the normal app-bundle executable is checked before PATH aliases.
    """

    override = os.environ.get("WBCP_CHROMIUM_EXECUTABLE", "").strip()
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
        return None
    if sys.platform == "darwin":
        for candidate in (
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
            Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            Path.home() / "Applications/Chromium.app/Contents/MacOS/Chromium",
        ):
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome"):
        resolved = shutil.which(name)
        if resolved:
            return resolved
    return None
