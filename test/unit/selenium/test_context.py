"""Unit tests for context.py - GalaxySeleniumContextImpl outside the test framework."""

import argparse
import os
import zipfile
from unittest.mock import Mock

from galaxy.selenium import (
    cli,
    driver_factory,
    jupyter_context,
)
from galaxy.selenium.context import (
    GalaxySeleniumContext,
    GalaxySeleniumContextImpl,
)
from galaxy.selenium.navigates_galaxy import WAIT_TYPES
from galaxy.selenium.stories import Story
from .util import skip_unless_playwright_browser_cached

CONFIG = {"driver": {"backend_type": "playwright", "headless": True}, "timeout_multiplier": 3}


class BrowserlessContext(GalaxySeleniumContextImpl):
    def __init__(self):
        # Skip building a ConfiguredDriver, which would launch a browser.
        pass

    def save_screenshot(self, path: str) -> None:
        with open(path, "wb") as f:
            f.write(b"screenshot")


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


def test_screenshots_are_saved_by_label_without_a_story(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    context = BrowserlessContext()

    assert context.screenshot("upload") == "upload.png"
    assert os.listdir(tmp_path) == ["upload.png"]


def test_assigned_story_collects_screenshots_in_its_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    story_dir = tmp_path / "story"
    story_dir.mkdir()
    context = BrowserlessContext()
    context.story = Story("T", "", str(story_dir))

    assert context.screenshot("upload", "The upload button") == str(story_dir / "000_upload.png")
    assert context.screenshot("done") == str(story_dir / "001_done.png")
    # The usual label-named copy is still written outside the story.
    assert (tmp_path / "upload.png").read_bytes() == (story_dir / "000_upload.png").read_bytes()
    assert (tmp_path / "done.png").exists()

    context.story.finalize()
    with zipfile.ZipFile(f"{story_dir}.zip") as archive:
        assert {"000_upload.png", "001_done.png"} <= set(archive.namelist())


def _cli_driver_wrapper(monkeypatch) -> cli.DriverWrapper:
    monkeypatch.setattr(driver_factory, "get_playwright_driver", lambda **kwds: Mock())
    parser = cli.add_selenium_arguments(argparse.ArgumentParser())
    args = parser.parse_args(["--backend", "playwright", "--galaxy_url", "http://example.org/galaxy/"])
    return cli.DriverWrapper(args)


def test_cli_driver_wrapper_is_a_context(monkeypatch):
    wrapper = _cli_driver_wrapper(monkeypatch)
    assert isinstance(wrapper, GalaxySeleniumContext)
    assert wrapper.build_url("api/version") == "http://example.org/galaxy/api/version"
    assert wrapper.build_url("api/version", for_selenium=False) == "http://example.org/galaxy/api/version"


def test_cli_screenshots_go_only_to_an_assigned_story(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wrapper = _cli_driver_wrapper(monkeypatch)
    saved: list[str] = []
    monkeypatch.setattr(wrapper, "save_screenshot", saved.append)

    assert wrapper.screenshot("before") is None
    assert saved == []

    wrapper.story = Story("T", "", str(tmp_path))
    assert wrapper.screenshot("upload", "The upload button") == str(tmp_path / "000_upload.png")
    assert saved == [str(tmp_path / "000_upload.png")]
