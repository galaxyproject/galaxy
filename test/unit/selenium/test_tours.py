"""Tour loading shared with Galaxy's tour registry, and narrating tours into stories."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import cast

from galaxy.navigation.tours import (
    get_tour_id_from_path,
    load_tour_from_path,
)
from galaxy.selenium.stories import Story
from galaxy.selenium.stories.tours import StoryTourCallback
from galaxy.selenium.web_element_protocol import WebElementProtocol
from .browserless import BrowserlessContext

TOUR = """
name: Example Tour
description: Walks the example.
title_default: Example Tour Step
steps:
    - content: "Welcome to <b>Galaxy</b>."
    - title: "Open the Upload Activity"
      component: upload_activity.activity
      intro: "Use this button."
      position: right
"""


def _write_tour(tmp_path):
    path = tmp_path / "example.tour.yaml"
    path.write_text(TOUR)
    return path


def test_tour_id_is_the_file_name_without_extension(tmp_path):
    assert get_tour_id_from_path(_write_tour(tmp_path)) == "example.tour"


def test_steps_are_normalized_for_the_client(tmp_path):
    tour = load_tour_from_path(_write_tour(tmp_path))
    first, second = tour["steps"]
    assert tour["requirements"] == []
    assert first["title"] == "Example Tour Step"
    assert first["orphan"] is True
    assert second["content"] == "Use this button."
    assert "intro" not in second
    assert second["placement"] == "right"
    assert "component" not in second
    assert second["element"]


def test_components_can_be_left_for_the_caller_to_resolve(tmp_path):
    tour = load_tour_from_path(_write_tour(tmp_path), resolve_components=False)
    second = tour["steps"][1]
    assert second["component"] == "upload_activity.activity"
    assert second["content"] == "Use this button."
    assert "element" not in second


class HighlightingContext(BrowserlessContext):
    """Records highlights and which screenshots were taken while one was drawn."""

    def __init__(self):
        self.highlighted: list[WebElementProtocol] = []
        self.highlighted_screenshots: list[str] = []
        self._highlighting = False

    def save_screenshot(self, path: str) -> None:
        super().save_screenshot(path)
        if self._highlighting:
            self.highlighted_screenshots.append(path)

    @contextmanager
    def highlight_element(self, element: WebElementProtocol) -> Iterator[None]:
        self.highlighted.append(element)
        self._highlighting = True
        try:
            yield
        finally:
            self._highlighting = False


def _walk(context: HighlightingContext, tmp_path, element: WebElementProtocol) -> None:
    """Hand each step to the callback the way run_tour does, the second step having a target."""
    tour = load_tour_from_path(_write_tour(tmp_path), resolve_components=False)
    callback = StoryTourCallback(context)
    for index, step in enumerate(tour["steps"]):
        callback.handle_step(step, index, element if index == 1 else None)


def test_tour_steps_become_story_sections(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    story_dir = tmp_path / "story"
    story_dir.mkdir()
    context = HighlightingContext()
    context.story = Story("Example Tour", "", str(story_dir))
    element = cast(WebElementProtocol, object())

    _walk(context, tmp_path, element)
    context.story.finalize()

    markdown = (story_dir / "story.md").read_text()
    sections = [
        "## Example Tour Step\n",
        "](000_step_0.png)",
        "Welcome to <b>Galaxy</b>.",
        "## Open the Upload Activity\n",
        "](001_step_1.png)",
        "Use this button.",
    ]
    positions = [markdown.index(section) for section in sections]
    assert positions == sorted(positions)
    assert context.highlighted == [element]
    assert context.highlighted_screenshots == [str(story_dir / "001_step_1.png")]
    # Tour text is HTML; the sanitizer keeps its basic markup.
    assert "Welcome to <b>Galaxy</b>." in (story_dir / "story.html").read_text()


def test_tours_without_a_story_are_left_alone(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    context = HighlightingContext()

    _walk(context, tmp_path, cast(WebElementProtocol, object()))

    assert context.highlighted == []
    assert sorted(p.name for p in tmp_path.iterdir()) == ["example.tour.yaml"]
