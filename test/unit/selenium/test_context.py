"""Unit tests for context.py - GalaxySeleniumContextImpl outside the test framework."""

from galaxy.selenium.context import GalaxySeleniumContextImpl
from galaxy.selenium.navigates_galaxy import WAIT_TYPES
from .util import skip_unless_playwright_browser_cached


@skip_unless_playwright_browser_cached()
def test_context_from_dict():
    context = GalaxySeleniumContextImpl(
        {"driver": {"backend_type": "playwright", "headless": True}, "timeout_multiplier": 3}
    )
    try:
        assert context.configured_driver.backend_type == "playwright"
        assert context.wait_length(WAIT_TYPES.UX_RENDER) == WAIT_TYPES.UX_RENDER.default_length * 3
    finally:
        context.configured_driver.quit()
