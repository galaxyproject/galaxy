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
from galaxy.datatypes.registry import Registry as DatatypesRegistry
from galaxy.model.triggers.update_audit_table import install as install_timestamp_triggers
from .. import MockObjectStore

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


@pytest.fixture(scope="module")
def db_url() -> str:
    """
    By default, use an in-memory database.
    To overwrite, add this fixture with a new db url to a test module.
    """
    return "sqlite:///:memory:"


@pytest.fixture(scope="module")
def engine(db_url: str) -> "Engine":
    return create_engine(db_url)


@pytest.fixture
def session(engine: "Engine") -> Session:
    return Session(engine)


@pytest.fixture(autouse=True, scope="module")
def init_database(engine: "Engine") -> None:
    """Create database objects."""
    m.mapper_registry.metadata.create_all(engine)
    install_timestamp_triggers(engine)


@pytest.fixture(autouse=True, scope="module")
def init_object_store() -> None:
    m.Dataset.object_store = MockObjectStore()  # type:ignore[assignment]


@pytest.fixture(autouse=True, scope="module")
def init_datatypes() -> None:
    datatypes_registry = DatatypesRegistry()
    datatypes_registry.load_datatypes()
    m.set_datatypes_registry(datatypes_registry)


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
