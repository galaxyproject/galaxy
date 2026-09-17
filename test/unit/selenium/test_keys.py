"""Keyboard vocabulary and validation tests that do not require browsers."""

from unittest.mock import Mock

import pytest
from selenium.webdriver.common.keys import Keys

from galaxy.selenium.has_driver import HasDriver
from galaxy.selenium.has_playwright_driver import HasPlaywrightDriver
from galaxy.selenium.keys import (
    Key,
    MODIFIER_KEYS,
    validate_key_press,
    validate_modifiers,
)
from galaxy.selenium.selenium_keys import (
    KEY_TO_SELENIUM,
    SELENIUM_KEY_TO_PLAYWRIGHT,
    SELENIUM_MODIFIERS,
)


def test_command_is_meta_alias():
    # Look up by name: mypy narrows Key.COMMAND to its own literal type and
    # cannot see that it is an alias.
    assert Key["COMMAND"] is Key.META
    assert MODIFIER_KEYS == {Key.ALT, Key.CONTROL, Key.META, Key.SHIFT}


@pytest.mark.parametrize("key", list(Key))
def test_each_named_key_has_selenium_encoding(key):
    assert SELENIUM_KEY_TO_PLAYWRIGHT[KEY_TO_SELENIUM[key]] == key.value


def test_legacy_return_and_modifiers():
    assert SELENIUM_KEY_TO_PLAYWRIGHT[Keys.RETURN] == Key.ENTER.value
    assert SELENIUM_MODIFIERS == {Keys.ALT, Keys.CONTROL, Keys.META, Keys.SHIFT}


@pytest.mark.parametrize("modifiers", [[], [Key.SHIFT], [Key.ALT, Key.CONTROL, Key.META, Key.SHIFT], [Key.COMMAND]])
def test_valid_modifiers(modifiers):
    validate_modifiers(modifiers)


@pytest.mark.parametrize(
    "modifiers", [[Key.ENTER], [Key.SPACE], ["Shift"], [None], [Key.SHIFT, Key.SHIFT], [Key.COMMAND, Key.META]]
)
@pytest.mark.parametrize("backend", [HasDriver, HasPlaywrightDriver])
def test_invalid_modifiers_have_no_browser_side_effects(backend, modifiers):
    driver = Mock()
    with pytest.raises(ValueError, match="modifier"):
        backend.press(driver, Key.TAB, modifiers=modifiers, element=Mock())
    assert driver.mock_calls == []


@pytest.mark.parametrize("key", ["", "ab", "Enter", "Control+a", "\n", Keys.SHIFT, None, 1])
@pytest.mark.parametrize("backend", [HasDriver, HasPlaywrightDriver])
def test_invalid_keys_have_no_browser_side_effects(backend, key):
    driver = Mock()
    with pytest.raises(ValueError, match="single printable character"):
        backend.press(driver, Key.TAB, key, modifiers=[Key.SHIFT], element=Mock())
    assert driver.mock_calls == []


@pytest.mark.parametrize("key", ["a", "A", "+", " ", Key.ENTER, Key.SPACE])
def test_valid_key_presses(key):
    validate_key_press([key], [Key.CONTROL])


@pytest.mark.parametrize("backend", [HasDriver, HasPlaywrightDriver])
def test_empty_press_has_no_browser_side_effects(backend):
    driver = Mock()
    backend.press(driver, modifiers=[Key.SHIFT], element=Mock())
    assert driver.mock_calls == []


def test_playwright_releases_modifiers_after_failure():
    driver = Mock()
    driver.page.keyboard.press.side_effect = RuntimeError("key failed")
    with pytest.raises(RuntimeError, match="key failed"):
        HasPlaywrightDriver.press(driver, Key.TAB, modifiers=[Key.CONTROL, Key.SHIFT])
    assert driver.page.keyboard.method_calls == [
        ("down", ("Control",), {}),
        ("down", ("Shift",), {}),
        ("press", ("Tab",), {}),
        ("up", ("Shift",), {}),
        ("up", ("Control",), {}),
    ]
