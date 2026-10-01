"""Tests for the story lifecycle inside the ``selenium_test`` decorator.

Driven with a stub test case rather than a browser. Skipped where ``galaxy_test``
is not importable - this directory is also the galaxy-selenium package's suite.
"""

import pytest

framework = pytest.importorskip("galaxy_test.selenium.framework")


class StubStory:
    def __init__(self, *args, **kwds):
        self.finalized = 0
        self.resets = 0
        self.documentation = []

    def finalize(self):
        self.finalized += 1

    def reset(self):
        self.resets += 1

    def add_documentation(self, content):
        self.documentation.append(content)


class StubTestCase:
    def __init__(self):
        self.story = None
        self.resets = 0

    def assert_baseline_accessibility(self):
        pass

    def document(self, content):
        self.story.add_documentation(content)

    def reset_driver_and_session(self):
        self.resets += 1


@pytest.fixture
def stories_enabled(tmp_path, monkeypatch):
    monkeypatch.setattr(framework, "GALAXY_TEST_STORIES_DIRECTORY", str(tmp_path))
    monkeypatch.setattr(framework, "Story", StubStory)
    monkeypatch.setattr(framework, "dump_test_information", lambda self, name: None)
    monkeypatch.setattr(framework, "GALAXY_TEST_SELENIUM_RETRIES", 0)
    return tmp_path


def test_story_written_once_on_success(stories_enabled):
    @framework.selenium_test
    def a_test(self):
        return "result"

    case = StubTestCase()
    assert a_test(case) == "result"
    assert case.story.finalized == 1


def test_story_written_once_on_failure_and_real_error_propagates(stories_enabled):
    @framework.selenium_test
    def a_test(self):
        raise AssertionError("the real failure")

    case = StubTestCase()
    with pytest.raises(AssertionError, match="the real failure"):
        a_test(case)
    assert case.story.finalized == 1
    assert "Test Failed" in case.story.documentation[0]


def test_story_write_failure_does_not_fail_a_passing_test(stories_enabled, monkeypatch):
    class Exploding(StubStory):
        def finalize(self):
            raise RuntimeError("story write failed")

    monkeypatch.setattr(framework, "Story", Exploding)

    @framework.selenium_test
    def a_test(self):
        return "result"

    # Writing documentation must not turn a green test red, nor trigger a retry.
    assert a_test(StubTestCase()) == "result"


def test_story_write_failure_does_not_replace_the_real_error(stories_enabled, monkeypatch):
    class Exploding(StubStory):
        def finalize(self):
            raise RuntimeError("story write failed")

    monkeypatch.setattr(framework, "Story", Exploding)

    @framework.selenium_test
    def a_test(self):
        raise AssertionError("the real failure")

    with pytest.raises(AssertionError, match="the real failure"):
        a_test(StubTestCase())


def test_retry_resets_the_story(stories_enabled, monkeypatch):
    monkeypatch.setattr(framework, "GALAXY_TEST_SELENIUM_RETRIES", 1)
    attempts = []

    @framework.selenium_test
    def a_test(self):
        attempts.append(1)
        if len(attempts) == 1:
            raise AssertionError("first attempt fails")
        return "result"

    case = StubTestCase()
    assert a_test(case) == "result"
    assert case.resets == 1
    assert case.story.resets == 1
    # Only the successful attempt is written out.
    assert case.story.finalized == 1


def test_no_story_directory_means_a_noop_story(tmp_path, monkeypatch):
    monkeypatch.setattr(framework, "GALAXY_TEST_STORIES_DIRECTORY", None)

    @framework.selenium_test
    def a_test(self):
        return "result"

    case = StubTestCase()
    assert a_test(case) == "result"
    assert isinstance(case.story, framework.NoopStory)
