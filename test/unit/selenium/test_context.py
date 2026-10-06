"""Unit tests for context.py - GalaxySeleniumContextImpl outside the test framework."""

from unittest.mock import Mock

from galaxy.selenium import (
    driver_factory,
    jupyter_context,
)
from galaxy.selenium.context import GalaxySeleniumContextImpl
from galaxy.selenium.navigates_galaxy import WAIT_TYPES
from .util import skip_unless_playwright_browser_cached

CONFIG = {"driver": {"backend_type": "playwright", "headless": True}, "timeout_multiplier": 3}


def test_jupyter_init_from_config(monkeypatch, tmp_path):
    # Runs without a browser: only the launch is stubbed, ConfiguredDriver is real.
    monkeypatch.setattr(driver_factory, "get_playwright_driver", lambda **kwds: Mock())
    # init() prefers a galaxy_selenium_context.yml in the working directory.
    monkeypatch.chdir(tmp_path)
    context = jupyter_context.init(CONFIG)
    assert isinstance(context, jupyter_context.JupyterContextImpl)
    assert context.wait_length(WAIT_TYPES.UX_RENDER) == WAIT_TYPES.UX_RENDER.default_length * 3


@skip_unless_playwright_browser_cached()
def test_context_from_dict():
    context = GalaxySeleniumContextImpl(CONFIG)
    try:
        assert context.configured_driver.backend_type == "playwright"
        assert context.wait_length(WAIT_TYPES.UX_RENDER) == WAIT_TYPES.UX_RENDER.default_length * 3
    finally:
        context.configured_driver.quit()
