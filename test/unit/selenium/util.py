"""Pytest-specific utility functions and decorators for selenium unit tests."""

from typing import (
    Callable,
    TypeVar,
    Union,
)

import pytest
from typing_extensions import ParamSpec

from galaxy.selenium.availability import (
    check_playwright_cached,
    check_selenium_cached,
    is_playwright_browser_available,
    is_selenium_browser_available,
    PLAYWRIGHT_BROWSER_NOT_AVAILABLE_MESSAGE,
    SELENIUM_BROWSER_NOT_AVAILABLE_MESSAGE,
)

P = ParamSpec("P")
T = TypeVar("T")


def _identity(func: Callable[P, T]) -> Callable[P, T]:
    """Identity function that returns the input function unchanged."""
    return func


def skip_unless_selenium_browser() -> Union[Callable[[Callable[P, T]], Callable[P, T]], pytest.MarkDecorator]:
    """
    Skip test if Selenium Chrome browser is not available.

    Returns:
        Either identity function (if browser available) or pytest skip marker with instructions
    """
    if is_selenium_browser_available():
        return _identity
    return pytest.mark.skip(SELENIUM_BROWSER_NOT_AVAILABLE_MESSAGE)


def skip_unless_playwright_browser() -> Union[Callable[[Callable[P, T]], Callable[P, T]], pytest.MarkDecorator]:
    """
    Skip test if Playwright Chromium browser is not available.

    Returns:
        Either identity function (if browser available) or pytest skip marker with instructions
    """
    if is_playwright_browser_available():
        return _identity
    return pytest.mark.skip(PLAYWRIGHT_BROWSER_NOT_AVAILABLE_MESSAGE)


def skip_unless_selenium_browser_cached() -> Union[Callable[[Callable[P, T]], Callable[P, T]], pytest.MarkDecorator]:
    """
    Skip test if Selenium Chrome browser is not available (cached check).

    This version caches the browser availability check to avoid repeatedly
    launching browsers during test collection.

    Returns:
        Either identity function (if browser available) or pytest skip marker with instructions
    """
    if check_selenium_cached():
        return _identity
    return pytest.mark.skip(SELENIUM_BROWSER_NOT_AVAILABLE_MESSAGE)


def skip_unless_playwright_browser_cached() -> Union[Callable[[Callable[P, T]], Callable[P, T]], pytest.MarkDecorator]:
    """
    Skip test if Playwright Chromium browser is not available (cached check).

    This version caches the browser availability check to avoid repeatedly
    launching browsers during test collection.

    Returns:
        Either identity function (if browser available) or pytest skip marker with instructions
    """
    if check_playwright_cached():
        return _identity
    return pytest.mark.skip(PLAYWRIGHT_BROWSER_NOT_AVAILABLE_MESSAGE)


# Re-export the cached check functions for use in conftest.py and test files
__all__ = (
    "skip_unless_selenium_browser",
    "skip_unless_playwright_browser",
    "skip_unless_selenium_browser_cached",
    "skip_unless_playwright_browser_cached",
    "check_selenium_cached",
    "check_playwright_cached",
)
