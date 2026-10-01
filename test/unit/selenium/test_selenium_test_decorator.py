"""Exercise the decorator with real stories and a browserless test case.

Skipped in the standalone galaxy-selenium suite, which does not ship galaxy_test.
"""

import datetime
import zipfile
from pathlib import Path

import pytest

framework = pytest.importorskip("galaxy_test.selenium.framework")


class BrowserlessTestCase:
    def __init__(self):
        self.resets = 0

    def assert_baseline_accessibility(self):
        pass

    def document(self, content):
        self.story.add_documentation(content)

    def reset_driver_and_session(self):
        self.resets += 1


@pytest.fixture
def story_run(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr(framework, "GALAXY_TEST_STORIES_DIRECTORY", str(tmp_path))
    monkeypatch.setattr(framework, "GALAXY_TEST_ERRORS_DIRECTORY", None)
    monkeypatch.setattr(framework, "GALAXY_TEST_SELENIUM_RETRIES", 0)
    monkeypatch.setattr("galaxy.selenium.stories.story.weasyprint_available", lambda: False)
    return mocker.spy(framework.Story, "finalize")


@pytest.mark.parametrize("fails", [False, True])
def test_story_artifacts_preserve_the_test_result(story_run, tmp_path, fails):
    failure = AssertionError("the real failure")

    @framework.selenium_test
    def a_test(self):
        """A story description."""
        self.document("Collected narration.")
        if fails:
            raise failure
        return "result"

    case = BrowserlessTestCase()
    if fails:
        with pytest.raises(AssertionError) as exc:
            a_test(case)
        assert exc.value is failure
    else:
        assert a_test(case) == "result"

    assert story_run.call_count == 1
    directory = Path(case.story.output_directory)
    markdown = (directory / "story.md").read_text()
    assert markdown.startswith("# a_test\n")
    assert "A story description." in markdown
    assert "Collected narration." in markdown
    assert ("Test Failed" in markdown) == fails
    assert (tmp_path / "latest").resolve() == directory
    with zipfile.ZipFile(f"{directory}.zip") as archive:
        assert archive.read("story.md").decode() == markdown
        assert "Collected narration." in archive.read("story.html").decode()


@pytest.mark.parametrize("fails", [False, True])
def test_archive_failure_does_not_change_the_test_result(story_run, monkeypatch, fails):
    def fail_archive(*args, **kwargs):
        raise OSError("archive write failed")

    monkeypatch.setattr(zipfile, "ZipFile", fail_archive)
    monkeypatch.setattr(framework, "GALAXY_TEST_SELENIUM_RETRIES", 1)
    failure = AssertionError("the real failure")

    @framework.selenium_test
    def a_test(self):
        if fails:
            raise failure
        return "result"

    case = BrowserlessTestCase()
    if fails:
        with pytest.raises(AssertionError) as exc:
            a_test(case)
        assert exc.value is failure
    else:
        assert a_test(case) == "result"
    assert case.resets == int(fails)
    assert story_run.call_count == 1
    assert (Path(case.story.output_directory) / "story.md").exists()


def test_retry_discards_failed_attempt_content(story_run, monkeypatch):
    monkeypatch.setattr(framework, "GALAXY_TEST_SELENIUM_RETRIES", 1)

    @framework.selenium_test
    def a_test(self):
        if self.resets == 0:
            self.document("Discarded narration.")
            self.story.screenshot_counter = 7
            raise AssertionError("first attempt fails")
        assert self.story.screenshot_counter == 0
        self.document("Retained narration.")
        return "result"

    case = BrowserlessTestCase()
    assert a_test(case) == "result"
    assert case.resets == 1
    assert story_run.call_count == 1
    markdown = (Path(case.story.output_directory) / "story.md").read_text()
    assert "Discarded narration." not in markdown
    assert "Retained narration." in markdown
    assert "Test Failed" not in markdown


def test_disabled_stories_write_nothing(story_run, tmp_path, monkeypatch):
    monkeypatch.setattr(framework, "GALAXY_TEST_STORIES_DIRECTORY", None)

    @framework.selenium_test
    def a_test(self):
        self.document("Ignored narration.")
        return "result"

    case = BrowserlessTestCase()
    assert a_test(case) == "result"
    assert isinstance(case.story, framework.NoopStory)
    assert story_run.call_count == 0
    assert list(tmp_path.iterdir()) == []


def test_run_directories_are_unique_at_the_same_time(tmp_path, monkeypatch):
    class FrozenDatetime(datetime.datetime):
        @classmethod
        def now(cls):
            return cls(2026, 10, 1, 12, 0)

    monkeypatch.setattr(framework.datetime, "datetime", FrozenDatetime)
    first = framework.run_directory(str(tmp_path), "test_example_")
    second = framework.run_directory(str(tmp_path), "test_example_")

    assert first != second
    assert len(list(tmp_path.iterdir())) == 2
