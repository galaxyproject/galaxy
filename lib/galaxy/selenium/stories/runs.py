"""Lifecycle of the story written for one run of a test or script."""

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


def run_directory(base_directory: str, name_prefix: str) -> str:
    """Create a directory for one run's artifacts, named for what ran and when."""
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
    """Start a story in a fresh run directory, or a no-op story when stories are disabled.

    Never raises - an unusable directory disables the story instead of failing the test.
    """
    if not base_directory:
        return NoopStory()
    try:
        directory = run_directory(os.path.abspath(base_directory), name_prefix)
    except Exception:
        log.exception("Failed to create story directory under %s, disabling the story", base_directory)
        return NoopStory()
    return Story(title, description, directory)


def write_story(story: StoryBase, failure_documentation: str | None = None) -> None:
    """Finalize ``story`` and link it as ``latest``; never raises so artifacts can't mask the run's result.

    ``failure_documentation`` is appended as markdown when the run failed.
    """
    if not story.enabled:
        return
    try:
        if failure_documentation:
            story.add_documentation(failure_documentation)
        story.finalize()
    except Exception:
        log.exception("Failed to write story to %s", story.output_directory)
        return
    link_latest(story.output_directory)
