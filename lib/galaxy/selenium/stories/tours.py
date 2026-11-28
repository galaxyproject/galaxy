"""Narrate Galaxy tours into stories."""

from contextlib import (
    AbstractContextManager,
    nullcontext,
)
from typing import (
    Any,
    Protocol,
)

from galaxy.selenium.navigates_galaxy import TourCallbackProtocol
from galaxy.selenium.web_element_protocol import WebElementProtocol
from .story import StoryBase


class NarratesScreenshots(Protocol):
    """The parts of a ``GalaxySeleniumContext`` a tour narration uses."""

    story: StoryBase

    def screenshot(self, label: str, caption: str | None = None) -> Any: ...

    def document(self, markdown_content: str) -> None: ...

    def highlight_element(self, element: WebElementProtocol) -> AbstractContextManager[None]: ...


class StoryTourCallback(TourCallbackProtocol):
    """Add each step to the context's story: a screenshot with its target highlighted, then its text."""

    def __init__(self, context: NarratesScreenshots) -> None:
        self.context = context

    def handle_step(self, step: dict[str, Any], step_index: int, element: WebElementProtocol | None = None) -> None:
        if not self.context.story.enabled:
            # Without a story, leave the page alone - no highlight restyling.
            return
        highlight = self.context.highlight_element(element) if element is not None else nullcontext()
        with highlight:
            self.context.screenshot(f"step_{step_index}", step.get("title"))
        if content := step.get("content"):
            self.context.document(content)
