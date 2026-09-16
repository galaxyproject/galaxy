"""Backend-neutral key names for the driver gesture vocabulary.

Tests and page objects name keys with ``Key``; each driver backend maps it onto
its own constants. Keeping the names here means nothing outside a backend
implementation needs to import Selenium's ``Keys`` or know Playwright's key-name
strings.
"""

from enum import Enum


class Key(str, Enum):
    """A key, named independently of any browser automation backend."""

    # Modifiers
    ALT = "alt"
    COMMAND = "command"
    CONTROL = "control"
    META = "meta"
    SHIFT = "shift"

    # Editing
    BACKSPACE = "backspace"
    DELETE = "delete"
    ENTER = "enter"
    ESCAPE = "escape"
    SPACE = "space"
    TAB = "tab"

    # Navigation
    ARROW_DOWN = "arrow_down"
    ARROW_LEFT = "arrow_left"
    ARROW_RIGHT = "arrow_right"
    ARROW_UP = "arrow_up"
    END = "end"
    HOME = "home"
    PAGE_DOWN = "page_down"
    PAGE_UP = "page_up"


MODIFIER_KEYS = frozenset(
    {
        Key.ALT,
        Key.COMMAND,
        Key.CONTROL,
        Key.META,
        Key.SHIFT,
    }
)

__all__ = (
    "Key",
    "MODIFIER_KEYS",
)
