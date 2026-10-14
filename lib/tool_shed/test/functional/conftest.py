from collections.abc import Generator

import pytest
from playwright.sync_api import Browser
from xdist.scheduler import LoadScopeScheduling

from ..base.browser import ShedBrowser
from ..base.playwrightbrowser import PlaywrightShedBrowser


def playwright_browser(browser: Browser) -> Generator[ShedBrowser, None, None]:
    page = browser.new_page()
    yield PlaywrightShedBrowser(page)


shed_browser = pytest.fixture(scope="class")(playwright_browser)

# Test modules that create and reuse repositories of the same names, so each set has to run
# in file order against one tool shed. Every other module is a scope of its own.
SHARED_REPOSITORY_MODULES = [
    (
        "0000",
        "0010",
        "0020",
        "0030",
        "0040",
        "0050",
        "0300",
        "1000",
        "1010",
        "1020",
        "1030",
        "1040",
        "1050",
        "1200",
        "1210",
        "1230",
        "1300",
    ),
    ("0070", "1070"),
    ("0080", "1080"),
    ("0100", "1120"),
    ("0110", "1130"),
    ("0120", "1140"),
    ("0150", "1170"),
    ("0160", "1180"),
    ("0170", "1190"),
]
_MODULE_SCOPES = {number: f"repositories-{group[0]}" for group in SHARED_REPOSITORY_MODULES for number in group}


class SharedRepositoryScheduling(LoadScopeScheduling):  # type: ignore[misc]  # pytest-xdist is untyped
    def _split_scope(self, nodeid: str) -> str:
        path = nodeid.split("::", 1)[0]
        number = path.rsplit("/", 1)[-1].removeprefix("test_")[:4]
        return _MODULE_SCOPES.get(number, path)


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_make_scheduler(config, log):
    if config.getvalue("dist") == "loadscope":
        return SharedRepositoryScheduling(config, log)
