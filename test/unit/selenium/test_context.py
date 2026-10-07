"""Unit tests for context.py - GalaxySeleniumContextImpl outside the test framework."""

from unittest.mock import Mock

import pytest

from galaxy.selenium import (
    driver_factory,
    jupyter_context,
)
from galaxy.selenium.context import GalaxySeleniumContextImpl
from galaxy.selenium.navigates_galaxy import WAIT_TYPES
from galaxy_test.selenium import jupyter_context as test_jupyter_context
from .util import skip_unless_playwright_browser_cached

CONFIG = {"driver": {"backend_type": "playwright", "headless": True}, "timeout_multiplier": 3}


@pytest.mark.parametrize(
    "init, context_class",
    [
        (jupyter_context.init, jupyter_context.JupyterContextImpl),
        (test_jupyter_context.init, test_jupyter_context.JupyterTestContextImpl),
    ],
)
def test_jupyter_init_from_config(monkeypatch, tmp_path, init, context_class):
    # Runs without a browser: only the launch is stubbed, ConfiguredDriver is real.
    monkeypatch.setattr(driver_factory, "get_playwright_driver", lambda **kwds: Mock())
    # init() prefers a galaxy_selenium_context.yml in the working directory.
    monkeypatch.chdir(tmp_path)
    context = init(CONFIG)
    assert isinstance(context, context_class)
    assert context.wait_length(WAIT_TYPES.UX_RENDER) == WAIT_TYPES.UX_RENDER.default_length * 3


@skip_unless_playwright_browser_cached()
def test_context_from_dict():
    context = GalaxySeleniumContextImpl(CONFIG)
    try:
        assert context.configured_driver.backend_type == "playwright"
        assert context.wait_length(WAIT_TYPES.UX_RENDER) == WAIT_TYPES.UX_RENDER.default_length * 3
    finally:
        context.configured_driver.quit()
