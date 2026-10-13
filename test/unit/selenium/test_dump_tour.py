"""gx-dump-tour writes a tour walk-through as a story, without a browser."""

import os
import time

import pytest

from galaxy.navigation.tours import load_tour_from_path
from galaxy.selenium.scripts import dump_tour
from .browserless import BrowserlessContext

TOUR = """
name: Example Tour
description: Walks the example.
steps:
    - title: "Welcome"
      content: "Welcome to Galaxy."
    - title: "History"
      content: "This is your history."
"""


class TourWalkingContext(BrowserlessContext):
    """Hands each step to the callback like run_tour, optionally failing after one."""

    def __init__(self, fail_after_step: int | None = None):
        self.fail_after_step = fail_after_step

    def _screenshot_path(self, label, extension=".png"):
        # Like the CLI's DriverWrapper, keep screenshots only in the story.
        return None

    def run_tour(self, path, skip_steps=None, sleep_on_steps=None, tour_callback=None):
        assert tour_callback is not None
        for index, step in enumerate(load_tour_from_path(path, resolve_components=False)["steps"]):
            tour_callback.handle_step(step, index)
            if index == self.fail_after_step:
                raise AssertionError("element never appeared")


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


def test_failed_dump_keeps_the_steps_reached(tmp_path, tour_path):
    output = tmp_path / "dumps"
    with pytest.raises(AssertionError, match="element never appeared"):
        dump_tour.dump_tour(TourWalkingContext(fail_after_step=0), tour_path, str(output))

    markdown = _markdown(str(output / "latest"))
    assert markdown.index("Welcome to Galaxy.") < markdown.index("Tour Failed")
    assert "This is your history." not in markdown
