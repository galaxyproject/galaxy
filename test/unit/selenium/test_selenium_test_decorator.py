"""Exercise ``selenium_test`` and screenshot routing with real stories and no browser.

The story lifecycle itself is tested in ``test_story.py``; this covers the glue in
``galaxy_test.selenium.framework``. Skipped in the standalone galaxy-selenium
suite, which does not ship galaxy_test.
"""

import os
import unittest
import zipfile
from pathlib import Path

import pytest

from galaxy.selenium.stories import (
    NoopStory,
    Story,
)

pytest.importorskip("galaxy_test.selenium.framework")

from galaxy_test.selenium import framework


class BrowserlessTestCase(framework.TestWithSeleniumMixin):
    """The real test mixin with the browser-facing operations stubbed out."""

    def __init__(self, accessibility_error: Exception | None = None):
        self.resets = 0
        self.accessibility_error = accessibility_error

    def save_screenshot(self, path: str) -> None:
        with open(path, "wb") as f:
            f.write(f"screenshot of attempt {self.resets}".encode())

    def reset_driver_and_session(self):
        self.resets += 1

    def assert_baseline_accessibility(self):
        if self.accessibility_error:
            raise self.accessibility_error


@pytest.fixture(autouse=True)
def framework_config(monkeypatch):
    """Everything off, regardless of the environment running these tests."""
    monkeypatch.setattr(framework, "GALAXY_TEST_STORIES_DIRECTORY", None)
    monkeypatch.setattr(framework, "GALAXY_TEST_SCREENSHOTS_DIRECTORY", None)
    monkeypatch.setattr(framework, "GALAXY_TEST_ERRORS_DIRECTORY", None)
    monkeypatch.setattr(framework, "GALAXY_TEST_SELENIUM_RETRIES", 0)
    # Keep the zip contents the same whether or not weasyprint can load here.
    monkeypatch.setattr("galaxy.selenium.stories.story.weasyprint_available", lambda: False)


@pytest.fixture
def stories_directory(tmp_path, monkeypatch):
    directory = tmp_path / "stories"
    monkeypatch.setattr(framework, "GALAXY_TEST_STORIES_DIRECTORY", str(directory))
    return directory


@pytest.fixture
def finalize_spy(mocker):
    return mocker.spy(Story, "finalize")


def _markdown(case: BrowserlessTestCase) -> str:
    return (Path(case.story.output_directory) / "story.md").read_text()


def test_success_writes_the_story_once(stories_directory, finalize_spy):
    def a_test(self):
        self.document("Collected narration.")
        self.screenshot("upload_button", "The upload button")
        return "result"

    # Set explicitly - Python 3.13+ already dedents docstrings at compile time, 3.10-3.12 don't.
    a_test.__doc__ = "Indented docstrings must not become code blocks.\n\n        Second paragraph.\n        "
    a_test = framework.selenium_test(a_test)

    case = BrowserlessTestCase()
    assert a_test(case) == "result"

    assert finalize_spy.call_count == 1
    directory = Path(case.story.output_directory)
    assert directory.parent == stories_directory
    assert directory.name.startswith("BrowserlessTestCase_a_test_")
    markdown = _markdown(case)
    assert markdown.startswith("# a_test\n")
    assert "\nIndented docstrings must not become code blocks.\n\nSecond paragraph.\n" in markdown
    assert "Collected narration." in markdown
    assert "## The upload button\n" in markdown
    assert "Test Failed" not in markdown
    assert (stories_directory / "latest").resolve() == directory.resolve()
    with zipfile.ZipFile(f"{directory}.zip") as archive:
        assert sorted(archive.namelist()) == ["000_upload_button.png", "story.html", "story.md"]


def test_skip_writes_the_story_without_retrying(stories_directory, finalize_spy, monkeypatch):
    monkeypatch.setattr(framework, "GALAXY_TEST_SELENIUM_RETRIES", 1)

    @framework.selenium_test
    def a_test(self):
        self.document("Before the skip.")
        raise unittest.SkipTest("not today")

    case = BrowserlessTestCase()
    with pytest.raises(unittest.SkipTest):
        a_test(case)

    assert case.resets == 0
    assert finalize_spy.call_count == 1
    markdown = _markdown(case)
    assert "Before the skip." in markdown
    assert "Test Failed" not in markdown


def test_final_failure_reraises_and_marks_the_story(stories_directory, finalize_spy, monkeypatch):
    monkeypatch.setattr(framework, "GALAXY_TEST_SELENIUM_RETRIES", 1)
    failure = AssertionError("the real failure")

    @framework.selenium_test
    def a_test(self):
        self.document(f"Narration from attempt {self.resets}.")
        raise failure

    case = BrowserlessTestCase()
    with pytest.raises(AssertionError) as exc:
        a_test(case)

    assert exc.value is failure
    assert case.resets == 1
    # Written once, for the final attempt only.
    assert finalize_spy.call_count == 1
    markdown = _markdown(case)
    assert "Narration from attempt 0." not in markdown
    assert markdown.index("Narration from attempt 1.") < markdown.index("Test Failed")


def test_accessibility_failure_fails_the_story(stories_directory, finalize_spy):
    failure = AssertionError("inaccessible")

    @framework.selenium_test
    def a_test(self):
        return "result"

    case = BrowserlessTestCase(accessibility_error=failure)
    with pytest.raises(AssertionError) as exc:
        a_test(case)

    assert exc.value is failure
    assert finalize_spy.call_count == 1
    assert "Test Failed" in _markdown(case)


def test_retry_discards_the_failed_attempt(stories_directory, finalize_spy, monkeypatch):
    monkeypatch.setattr(framework, "GALAXY_TEST_SELENIUM_RETRIES", 1)

    @framework.selenium_test
    def a_test(self):
        self.screenshot(f"attempt_{self.resets}")
        if self.resets == 0:
            self.document("Discarded narration.")
            raise AssertionError("first attempt fails")
        self.document("Retained narration.")
        return "result"

    case = BrowserlessTestCase()
    assert a_test(case) == "result"

    assert case.resets == 1
    assert finalize_spy.call_count == 1
    markdown = _markdown(case)
    assert "Discarded narration." not in markdown
    assert "Retained narration." in markdown
    assert "Test Failed" not in markdown
    # The retry's numbering starts over; the discarded screenshot stays on disk but is not shipped.
    assert "(000_attempt_1.png)" in markdown
    directory = case.story.output_directory
    assert sorted(os.listdir(directory)) == ["000_attempt_0.png", "000_attempt_1.png", "story.html", "story.md"]
    with zipfile.ZipFile(f"{directory}.zip") as archive:
        assert sorted(archive.namelist()) == ["000_attempt_1.png", "story.html", "story.md"]


def test_disabled_stories_write_nothing(tmp_path, finalize_spy, monkeypatch):
    monkeypatch.chdir(tmp_path)

    @framework.selenium_test
    def a_test(self):
        self.document("Ignored narration.")
        assert self.screenshot("ignored") is None
        return "result"

    case = BrowserlessTestCase()
    assert a_test(case) == "result"

    assert isinstance(case.story, NoopStory)
    assert finalize_spy.call_count == 0
    assert list(tmp_path.iterdir()) == []


def test_screenshots_directory_gets_a_copy_of_story_screenshots(stories_directory, tmp_path, monkeypatch):
    screenshots_directory = tmp_path / "screenshots"
    monkeypatch.setattr(framework, "GALAXY_TEST_SCREENSHOTS_DIRECTORY", str(screenshots_directory))

    @framework.selenium_test
    def a_test(self):
        self.screenshot("first", "A caption")
        self.screenshot("second")

    case = BrowserlessTestCase()
    a_test(case)

    directory = Path(case.story.output_directory)
    assert (directory / "000_first.png").read_bytes() == (screenshots_directory / "first.png").read_bytes()
    assert (directory / "001_second.png").read_bytes() == (screenshots_directory / "second.png").read_bytes()
    markdown = _markdown(case)
    assert "## A caption\n" in markdown
    # Without a caption the label is the heading.
    assert "## second\n" in markdown


def test_screenshots_directory_alone_keeps_plain_labels(tmp_path, monkeypatch):
    screenshots_directory = tmp_path / "screenshots"
    monkeypatch.setattr(framework, "GALAXY_TEST_SCREENSHOTS_DIRECTORY", str(screenshots_directory))

    @framework.selenium_test
    def a_test(self):
        self.screenshot("first")

    a_test(BrowserlessTestCase())

    assert os.listdir(screenshots_directory) == ["first.png"]
