"""Selenium key encoding and derived lookups for legacy send_keys() callers."""

from selenium.webdriver.common.keys import Keys

from .keys import (
    Key,
    MODIFIER_KEYS,
)

KEY_TO_SELENIUM: dict[Key, str] = {
    Key.ALT: Keys.ALT,
    Key.CONTROL: Keys.CONTROL,
    Key.META: Keys.META,
    Key.SHIFT: Keys.SHIFT,
    Key.BACKSPACE: Keys.BACKSPACE,
    Key.DELETE: Keys.DELETE,
    Key.ENTER: Keys.ENTER,
    Key.ESCAPE: Keys.ESCAPE,
    Key.SPACE: Keys.SPACE,
    Key.TAB: Keys.TAB,
    Key.ARROW_DOWN: Keys.ARROW_DOWN,
    Key.ARROW_LEFT: Keys.ARROW_LEFT,
    Key.ARROW_RIGHT: Keys.ARROW_RIGHT,
    Key.ARROW_UP: Keys.ARROW_UP,
    Key.END: Keys.END,
    Key.HOME: Keys.HOME,
    Key.PAGE_DOWN: Keys.PAGE_DOWN,
    Key.PAGE_UP: Keys.PAGE_UP,
}

# Keep the old character-stream API compatible without another maintained map.
SELENIUM_KEY_TO_PLAYWRIGHT = {encoded: key.value for key, encoded in KEY_TO_SELENIUM.items()}
SELENIUM_KEY_TO_PLAYWRIGHT[Keys.RETURN] = Key.ENTER.value
SELENIUM_MODIFIERS = frozenset(KEY_TO_SELENIUM[key] for key in MODIFIER_KEYS)
