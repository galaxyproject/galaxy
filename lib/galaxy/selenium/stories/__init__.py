"""Generation of narrative documentation - screenshots interleaved with markdown."""

from .runs import (
    link_latest,
    run_directory,
    story_for_run,
    write_story,
)
from .story import (
    NoopStory,
    Story,
    StoryBase,
)

__all__ = [
    "NoopStory",
    "Story",
    "StoryBase",
    "link_latest",
    "run_directory",
    "story_for_run",
    "write_story",
]
