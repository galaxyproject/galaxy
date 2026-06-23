import tempfile
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

from galaxy.model.unittest_utils.model_testing_utils import (
    _generate_unique_database_name,
    _make_sqlite_db_url,
)


@pytest.fixture(scope="module")
def sqlite_url_factory():
    """Return a function that generates a sqlite url"""

    def url():
        database = _generate_unique_database_name()
        return _make_sqlite_db_url(tmp_dir, database)

    with tempfile.TemporaryDirectory() as tmp_dir:
        yield url


@pytest.fixture(scope="module")
def db_url(sqlite_url_factory):  # noqa: F811
    return sqlite_url_factory()


@pytest.fixture()
def engine(db_url: str) -> "Engine":
    return create_engine(db_url)


@pytest.fixture
def session(engine: "Engine") -> Session:
    return Session(engine)
