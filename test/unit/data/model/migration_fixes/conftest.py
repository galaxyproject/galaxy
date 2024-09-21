from typing import (
    Generator,
    TYPE_CHECKING,
)

import pytest
from sqlalchemy import (
    create_engine,
    text,
)
from sqlalchemy.orm import Session

from galaxy import model as m

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

from galaxy.model.unittest_utils.model_testing_utils import (  # noqa: F401 - url_factory is a fixture we have to import explicitly
    sqlite_url_factory,
)


@pytest.fixture()
def db_url(sqlite_url_factory):  # noqa: F811
    return sqlite_url_factory()


@pytest.fixture()
def engine(db_url: str) -> "Engine":
    return create_engine(db_url)


@pytest.fixture
def session(engine: "Engine") -> Session:
    return Session(engine)


@pytest.fixture(autouse=True)
def clear_database(engine: "Engine") -> "Generator":
    """Delete all rows from all tables. Called after each test."""
    yield
    with engine.begin() as conn:
        for table in m.mapper_registry.metadata.tables:
            # Unless db is sqlite, disable foreign key constraints to delete out of order
            if engine.name != "sqlite":
                conn.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER ALL"))
            conn.execute(text(f"DELETE FROM {table}"))
