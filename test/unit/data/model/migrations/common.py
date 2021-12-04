import os
import uuid
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.sql.compiler import IdentifierPreparer

from galaxy.model.database_utils import create_database


# Fixture and helper functions used to generate urls for postgresql and sqlite databases

@pytest.fixture
def url_factory(tmp_directory):
    """
    Return a factory function that produces a database url with a unique database name.
    If _get_connection_url() returns a value, the database is postgresql; otherwise, it's
    sqlite (referring to a location witin the /tmp directory).
    """
    def url():
        database = _generate_unique_database_name()
        connection_url = _get_connection_url()
        if connection_url:
            return _make_postgres_db_url(connection_url, database)
        else:
            return _make_sqlite_db_url(tmp_directory, database)
    return url


@contextmanager
def disposing_engine(url):
    """Context manager for engine that disposes of its connection pool on exit."""
    engine = create_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()


@contextmanager
def create_and_drop_database(db_url):
    """
    Context manager that creates a database. If the database is postgresql, it is dropped on exit;
    a sqlite database should be removed automatically by tempfile.
    """
    try:
        create_database(db_url)
        yield
    finally:
        if _is_postgres(db_url):
            _drop_postgres_database(db_url)


def _generate_unique_database_name():
    return f'galaxytest_{uuid.uuid4().hex}'


def _get_connection_url():
    return os.environ.get('GALAXY_TEST_DBURI')


def _is_postgres(db_url):
    return db_url.startswith('postgres')


def _make_sqlite_db_url(tmpdir, database):
    path = os.path.join(tmpdir, database)
    return f'sqlite:///{path}'


def _make_postgres_db_url(connection_url, database):
    url = make_url(connection_url)
    url = url.set(database=database)
    return str(url)


def _drop_postgres_database(db_url):
    url = make_url(db_url)
    database = url.database
    connection_url = url.set(database='postgres')
    engine = create_engine(connection_url, isolation_level='AUTOCOMMIT')
    preparer = IdentifierPreparer(engine.dialect)
    database = preparer.quote(database)
    stmt = f'DROP DATABASE IF EXISTS {database}'
    with engine.connect() as conn:
        conn.execute(stmt)
    engine.dispose()
