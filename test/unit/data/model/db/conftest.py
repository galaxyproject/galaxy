from typing import (
    Generator,
    TYPE_CHECKING,
)

import pytest
from sqlalchemy import (
    create_engine,
    text,
)
from sqlalchemy.exc import IntegrityError
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
    session = Session(engine)
    # For sqlite, we need to explicitly enale foreign key constraints.
    if engine.name == "sqlite":
        session.execute(text("PRAGMA foreign_keys = ON;"))
    return session


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
def clear_database(engine: "Engine", session) -> "Generator":
    """Delete all rows from all tables. Called after each test."""
    yield

    # If a test left an open transaction, rollback to prevent database locking.
    if session.in_transaction():
        session.rollback()

    with engine.connect() as conn:
        if engine.name == "sqlite":
            conn.execute(text("PRAGMA foreign_keys = OFF;"))
            for table in m.mapper_registry.metadata.tables:
                conn.execute(text(f"DELETE FROM {table}"))
        else:
            # For postgres, we can disable foreign key constraints with this statement:
            #   conn.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER ALL"))
            # However, unless running as superuser, this will raise an error when trying
            #   to disable a system trigger. Disabling USER triggers instead of ALL
            #   won't work because the USER option excludes foreign key constraints.
            # The following is an alternative: we do multiple passes until all tables have been cleared:
            to_delete = list(m.mapper_registry.metadata.tables)
            failed = []
            while to_delete:
                for table in to_delete:
                    try:
                        conn.execute(text(f"DELETE FROM {table}"))
                    except IntegrityError:
                        failed.append(table)
                        conn.rollback()
                to_delete, failed = failed, []

        conn.commit()
