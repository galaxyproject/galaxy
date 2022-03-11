import os
import uuid
from contextlib import contextmanager
from typing import (
    Callable,
    Iterator,
    NewType,
    Optional,
)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import (
    Engine,
    make_url,
)
from sqlalchemy.sql.compiler import IdentifierPreparer

from galaxy.model.database_utils import create_database

DbUrl = NewType("DbUrl", str)

# Fixture and helper functions used to generate urls for postgresql and sqlite databases


@pytest.fixture
def url_factory(tmp_directory: str) -> Callable[[], DbUrl]:
    """
    Return a factory function that produces a database url with a unique database name.
    If _get_connection_url() returns a value, the database is postgresql; otherwise, it's
    sqlite (referring to a location witin the /tmp directory).
    """

    def url() -> DbUrl:
        database = _generate_unique_database_name()
        connection_url = _get_connection_url()
        if connection_url:
            return _make_postgres_db_url(DbUrl(connection_url), database)
        else:
            return _make_sqlite_db_url(tmp_directory, database)

    return url


@contextmanager
def disposing_engine(url: DbUrl) -> Iterator[Engine]:
    """Context manager for engine that disposes of its connection pool on exit."""
    engine = create_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()


@contextmanager
def create_and_drop_database(url: DbUrl) -> Iterator[None]:
    """
    Context manager that creates a database. If the database is postgresql, it is dropped on exit;
    a sqlite database should be removed automatically by tempfile.
    """
    try:
        create_database(url)
        yield
    finally:
        if _is_postgres(url):
            _drop_postgres_database(url)


@contextmanager
def drop_database(url: DbUrl) -> Iterator[None]:
    """
    Context manager that ensures a postgres database identified by url is dropped on exit;
    a sqlite database should be removed automatically by tempfile.
    """
    try:
        yield
    finally:
        if _is_postgres(url):
            _drop_postgres_database(url)


def _generate_unique_database_name() -> str:
    return f"galaxytest_{uuid.uuid4().hex}"


def _get_connection_url() -> Optional[str]:
    return os.environ.get("GALAXY_TEST_DBURI")


def _is_postgres(url: DbUrl) -> bool:
    return url.startswith("postgres")


def _make_sqlite_db_url(tmpdir: str, database: str) -> DbUrl:
    path = os.path.join(tmpdir, database)
    return DbUrl(f"sqlite:///{path}")


def _make_postgres_db_url(connection_url: DbUrl, database: str) -> DbUrl:
    url = make_url(connection_url)
    url = url.set(database=database)
    return DbUrl(str(url))


def _drop_postgres_database(url: DbUrl) -> None:
    db_url = make_url(url)
    database = db_url.database
    connection_url = db_url.set(database="postgres")
    engine = create_engine(connection_url, isolation_level="AUTOCOMMIT")
    preparer = IdentifierPreparer(engine.dialect)
    database = preparer.quote(database)
    stmt = f"DROP DATABASE IF EXISTS {database}"
    with engine.connect() as conn:
        conn.execute(stmt)
    engine.dispose()
