import pytest

from tool_shed.webapp.model import (
    Repository,
    User,
)
from ._util import (
    provides_repositories_fixture,
    random_name,
    repository_fixture,
    TestToolShedApp,
    user_fixture,
)


@pytest.fixture
def shed_app():
    app = TestToolShedApp()
    yield app


@pytest.fixture
def new_user(shed_app: TestToolShedApp) -> User:
    return user_fixture(shed_app, random_name())


@pytest.fixture
def new_repository(shed_app: TestToolShedApp, new_user: User) -> Repository:
    return repository_fixture(shed_app, new_user, random_name())


@pytest.fixture
def provides_repositories(shed_app: TestToolShedApp, new_user: User) -> User:
    return provides_repositories_fixture(shed_app, new_user)
