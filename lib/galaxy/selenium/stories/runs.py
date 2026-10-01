"""Lifecycle of the story written for one test run."""

import datetime
import logging
import os
import tempfile

from .story import (
    NoopStory,
    Story,
    StoryBase,
)

log = logging.getLogger(__name__)

FAILURE_DOCUMENTATION = "## Test Failed\n\nSee the error directory for details."


def run_directory(base_directory: str, name_prefix: str) -> str:
    """Create a directory for one run's artifacts, named for the test and the time."""
    os.makedirs(base_directory, exist_ok=True)
    prefix = name_prefix + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + "_"
    return tempfile.mkdtemp(prefix=prefix, dir=base_directory)


def link_latest(directory: str) -> None:
    """Point a ``latest`` symlink beside ``directory`` at it, ignoring failures."""
    link = os.path.join(os.path.dirname(directory), "latest")
    try:
        if os.path.lexists(link):
            os.remove(link)
        os.symlink(directory, link)
    except OSError:
        log.warning("Failed to link %s to %s", link, directory, exc_info=True)


def story_for_run(base_directory: str | None, name_prefix: str, title: str, description: str) -> StoryBase:
    """Start a story in a fresh run directory, or a no-op story when stories are disabled."""
    if not base_directory:
        return NoopStory()
    directory = run_directory(os.path.abspath(base_directory), name_prefix)
    return Story(title, description, directory)


def write_story(story: StoryBase, failed: bool = False) -> None:
    """Finalize ``story`` and link it as ``latest``; never raises so artifacts can't mask the test result."""
    if not story.enabled:
        return
    try:
        if failed:
            story.add_documentation(FAILURE_DOCUMENTATION)
        story.finalize()
    except Exception:
        log.exception("Failed to write story to %s", story.output_directory)
        return
    link_latest(story.output_directory)
