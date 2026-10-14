"""gx-dump-tour writes a tour walk-through as a story, without a browser."""

import os
import time

import pytest

import galaxy.selenium.cli as cli
import galaxy.selenium.scripts.dump_tour as dump_tour
from galaxy.selenium.stories import Story
from .browserless import BrowserlessContext

TOUR = """
name: Example Tour
description: Walks the example.
title_default: Welcome
steps:
    - intro: "Welcome to Galaxy."
    - title: "History"
      content: "This is your history."
"""


class TourWalkingContext(BrowserlessContext):
    """Runs real tour steps, optionally interrupting after documenting a step."""

    def __init__(self, failure: BaseException | None = None):
        self.failure = failure

    def home(self) -> None:
        pass

    def _screenshot_path(self, label, extension=".png"):
        # Like the CLI's DriverWrapper, keep screenshots only in the story.
        return None

    def document(self, markdown_content):
        super().document(markdown_content)
        if self.failure is not None:
            raise self.failure


@pytest.fixture
def tour_path(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    path = tmp_path / "example.yaml"
    path.write_text(TOUR)
    return str(path)


def _markdown(directory: str) -> str:
    with open(os.path.join(directory, "story.md")) as f:
        return f.read()


def test_dump_writes_a_story_per_run(tmp_path, tour_path):
    output = tmp_path / "dumps"
    first = dump_tour.dump_tour(TourWalkingContext(), tour_path, str(output))
    second = dump_tour.dump_tour(TourWalkingContext(), tour_path, str(output))

    assert first.output_directory != second.output_directory
    assert os.path.dirname(second.output_directory) == str(output)
    assert os.path.basename(second.output_directory).startswith("example_")
    assert (output / "latest").resolve() == (output / os.path.basename(second.output_directory)).resolve()
    markdown = _markdown(second.output_directory)
    assert markdown.startswith("# Example Tour\n")
    assert "Walks the example." in markdown
    assert markdown.index("## Welcome\n") < markdown.index("This is your history.")
    assert sorted(f for f in os.listdir(second.output_directory) if f.endswith(".png")) == [
        "000_step_0.png",
        "001_step_1.png",
    ]
    assert os.path.exists(f"{second.output_directory}.zip")


@pytest.mark.parametrize("failure", [AssertionError("element never appeared"), KeyboardInterrupt()])
def test_failed_dump_keeps_the_steps_reached(tmp_path, tour_path, failure):
    output = tmp_path / "dumps"
    with pytest.raises(type(failure)) as raised:
        dump_tour.dump_tour(TourWalkingContext(failure), tour_path, str(output))
    assert raised.value is failure

    markdown = _markdown(str(output / "latest"))
    assert markdown.index("Welcome to Galaxy.") < markdown.index("Tour Failed")
    assert "This is your history." not in markdown


def test_main_reports_story_write_failure(tmp_path, tour_path, monkeypatch, capsys):
    context = TourWalkingContext()
    finished = []
    monkeypatch.setattr(cli, "DriverWrapper", lambda args: context)
    monkeypatch.setattr(context, "finish", lambda: finished.append(True), raising=False)

    def fail_to_finalize(story):
        raise OSError("story disk full")

    monkeypatch.setattr(Story, "finalize", fail_to_finalize)
    with pytest.raises(OSError, match="story disk full"):
        dump_tour.main([tour_path, "-o", str(tmp_path / "dumps")])

    assert finished == [True]
    assert "Wrote" not in capsys.readouterr().out
    assert not (tmp_path / "dumps" / "latest").exists()


def test_story_write_failure_preserves_tour_failure(tmp_path, tour_path, monkeypatch):
    failure = KeyboardInterrupt()

    def fail_to_finalize(story):
        raise OSError("story disk full")

    monkeypatch.setattr(Story, "finalize", fail_to_finalize)
    with pytest.raises(KeyboardInterrupt) as raised:
        dump_tour.dump_tour(TourWalkingContext(failure), tour_path, str(tmp_path / "dumps"))
    assert raised.value is failure
