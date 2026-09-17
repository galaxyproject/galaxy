"""Backend-neutral keyboard vocabulary using standard KeyboardEvent.key values."""

from collections.abc import Sequence
from enum import Enum


class Key(str, Enum):
    """A named key; printable characters can be passed directly to press()."""

    # Modifiers
    ALT = "Alt"
    CONTROL = "Control"
    META = "Meta"
    COMMAND = "Meta"  # Alias for the same modifier on macOS.
    SHIFT = "Shift"

    # Editing
    BACKSPACE = "Backspace"
    DELETE = "Delete"
    ENTER = "Enter"
    ESCAPE = "Escape"
    SPACE = " "
    TAB = "Tab"

    # Navigation
    ARROW_DOWN = "ArrowDown"
    ARROW_LEFT = "ArrowLeft"
    ARROW_RIGHT = "ArrowRight"
    ARROW_UP = "ArrowUp"
    END = "End"
    HOME = "Home"
    PAGE_DOWN = "PageDown"
    PAGE_UP = "PageUp"


MODIFIER_KEYS = frozenset({Key.ALT, Key.CONTROL, Key.META, Key.SHIFT})


def validate_modifiers(modifiers: Sequence[Key]) -> None:
    """Require distinct modifier keys, including when aliases are supplied."""
    seen: set[Key] = set()
    for modifier in modifiers:
        if not isinstance(modifier, Key) or modifier not in MODIFIER_KEYS:
            raise ValueError(f"Expected a modifier Key, got {modifier!r}")
        if modifier in seen:
            raise ValueError(f"Duplicate modifier: {modifier!r}")
        seen.add(modifier)


def validate_key_press(keys: Sequence[Key | str], modifiers: Sequence[Key]) -> None:
    """Validate the whole gesture before either backend changes browser state."""
    validate_modifiers(modifiers)
    for key in keys:
        if isinstance(key, Key):
            continue
        if not isinstance(key, str) or len(key) != 1 or not key.isprintable():
            raise ValueError(f"Expected a Key or a single printable character, got {key!r}")


__all__ = (
    "Key",
    "MODIFIER_KEYS",
    "validate_modifiers",
    "validate_key_press",
)
