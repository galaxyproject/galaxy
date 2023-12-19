import os
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
)

import pytest
from playwright.sync_api import (
    Browser,
    BrowserContext,
)

from ..base.browser import ShedBrowser
from ..base.playwrightbrowser import PlaywrightShedBrowser
from ..base.twillbrowser import TwillShedBrowser

DEFAULT_BROWSER = "playwright"


def twill_browser() -> Generator[ShedBrowser, None, None]:
    yield TwillShedBrowser()


def playwright_browser(class_context: BrowserContext) -> Generator[ShedBrowser, None, None]:
    page = class_context.new_page()
    yield PlaywrightShedBrowser(page)


test_browser = os.environ.get("TOOL_SHED_TEST_BROWSER", DEFAULT_BROWSER)
if test_browser == "twill":
    shed_browser: Callable[..., Generator[ShedBrowser, None, None]] = pytest.fixture(scope="class")(twill_browser)
elif test_browser == "playwright":
    shed_browser = pytest.fixture(scope="class")(playwright_browser)
else:
    raise ValueError(f"Unrecognized value for TOOL_SHED_TEST_BROWSER: {test_browser}")


@pytest.fixture(scope="class")
def class_context(
    browser: Browser,
    browser_context_args: Dict,
    pytestconfig: Any,
    request: pytest.FixtureRequest,
) -> Generator[BrowserContext, None, None]:
    from pytest_playwright.pytest_playwright import context

    yield from context.__pytest_wrapped__.obj(browser, browser_context_args, pytestconfig, request)
