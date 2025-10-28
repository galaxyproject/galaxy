"""Story generation for visual test documentation.

This package provides tools for generating narrative documentation with
interleaved screenshots and markdown content. It can be used in tests,
standalone scripts, and Jupyter notebooks.
"""

from .story import (
    NoopStory,
    Story,
    StoryProtocol,
)

__all__ = [
    "Story",
    "NoopStory",
    "StoryProtocol",
]
