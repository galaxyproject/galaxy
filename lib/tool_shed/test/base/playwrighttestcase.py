import os
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page

from .playwrightbrowser import PlaywrightShedBrowser
from .twilltestcase import ShedTwillTestCase

SCREENSHOT_DIR_ENV = "TOOL_SHED_TEST_SCREENSHOTS"


class PlaywrightTestCase(ShedTwillTestCase):
    """Base class for Playwright-based frontend tests."""

    @property
    def _playwright_browser(self) -> PlaywrightShedBrowser:
        browser = self._browser
        assert isinstance(browser, PlaywrightShedBrowser)
        return browser

    @property
    def _page(self) -> Page:
        return self._playwright_browser._page

    def screenshot(self, name: str) -> None:
        """Save screenshot to TOOL_SHED_TEST_SCREENSHOTS if set.

        If target exists, moves old version to old/<name>-<datetime>.png
        """
        screenshot_dir = os.environ.get(SCREENSHOT_DIR_ENV)
        if not screenshot_dir:
            return

        base_path = Path(screenshot_dir)
        base_path.mkdir(parents=True, exist_ok=True)

        target = base_path / f"{name}.png"

        # Archive existing screenshot
        if target.exists():
            old_dir = base_path / "old"
            old_dir.mkdir(exist_ok=True)
            created = datetime.fromtimestamp(target.stat().st_mtime)
            archive_name = f"{name}-{created.strftime('%Y%m%d_%H%M%S')}.png"
            target.rename(old_dir / archive_name)

        self._page.screenshot(path=str(target))
