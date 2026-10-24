import ast
import re
from collections import defaultdict
from collections.abc import Generator
from pathlib import Path

import pytest
from playwright.sync_api import Browser
from xdist.scheduler import LoadScopeScheduling

from ..base.browser import ShedBrowser
from ..base.playwrightbrowser import PlaywrightShedBrowser


def playwright_browser(browser: Browser) -> Generator[ShedBrowser, None, None]:
    page = browser.new_page()
    yield PlaywrightShedBrowser(page)


shed_browser = pytest.fixture(scope="class")(playwright_browser)

# Repository names in the numbered test modules end in the number of the module that introduced
# them (filtering_0000); test_NNNN strings are tool panel section labels, not repositories.
REPOSITORY_NAME = re.compile(r"(?!test_)[a-z][a-z0-9_]*_\d{4}")


def repository_names(module: Path) -> set[str]:
    return {
        node.value
        for node in ast.walk(ast.parse(module.read_text()))
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and REPOSITORY_NAME.fullmatch(node.value)
    }


def shared_repository_scopes(directory: Path) -> dict[str, str]:
    """Map the test modules that use a repository name of another module to a common scope.

    Such modules create and reuse the same repositories, so they have to run in file order
    against one tool shed. Modules missing from the result are a scope of their own.
    """
    modules = sorted(module.name for module in directory.glob("test_*.py"))
    parent = {module: module for module in modules}

    def root(module: str) -> str:
        while parent[module] != module:
            module = parent[module]
        return module

    first_module_with_name: dict[str, str] = {}
    for module in modules:
        for name in repository_names(directory / module):
            other = first_module_with_name.setdefault(name, module)
            first, second = sorted((root(module), root(other)))
            parent[second] = first
    groups: dict[str, list[str]] = defaultdict(list)
    for module in modules:
        groups[root(module)].append(module)
    return {
        module: f"repositories-{first}" for first, members in groups.items() if len(members) > 1 for module in members
    }


class SharedRepositoryScheduling(LoadScopeScheduling):
    def __init__(self, config, log=None):
        super().__init__(config, log)
        self.module_scopes = shared_repository_scopes(Path(__file__).parent)

    def _split_scope(self, nodeid: str) -> str:
        path = nodeid.split("::", 1)[0]
        return self.module_scopes.get(path.rsplit("/", 1)[-1], path)


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_make_scheduler(config, log):
    if config.getvalue("dist") == "loadscope":
        return SharedRepositoryScheduling(config, log)
