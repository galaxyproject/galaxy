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
from sqlalchemy import (
    create_engine,
    delete,
    select,
)
from sqlalchemy.engine import (
    Engine,
    make_url,
)
from sqlalchemy.sql.compiler import IdentifierPreparer

from galaxy.model.database_utils import create_database

# GALAXY_TEST_CONNECT_POSTGRES_URI='postgresql://postgres@localhost:5432/postgres' pytest test/unit/model
skip_if_not_postgres_uri = pytest.mark.skipif(
    not os.environ.get("GALAXY_TEST_CONNECT_POSTGRES_URI"), reason="GALAXY_TEST_CONNECT_POSTGRES_URI not set"
)

# GALAXY_TEST_CONNECT_MYSQL_URI='mysql+mysqldb://root@localhost/mysql' pytest test/unit/model
skip_if_not_mysql_uri = pytest.mark.skipif(
    not os.environ.get("GALAXY_TEST_CONNECT_MYSQL_URI"), reason="GALAXY_TEST_CONNECT_MYSQL_URI not set"
)

DbUrl = NewType("DbUrl", str)


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
def drop_existing_database(url: DbUrl) -> Iterator[None]:
    """
    Context manager that ensures a postgres database identified by url is dropped on exit;
    a sqlite database should be removed automatically by tempfile.
    """
    try:
        yield
    finally:
        if _is_postgres(url):
            _drop_postgres_database(url)


@contextmanager
def disposing_engine(url: DbUrl) -> Iterator[Engine]:
    """Context manager for engine that disposes of its connection pool on exit."""
    engine = create_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()


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


@pytest.fixture(scope="module")
def url(tmp_directory: str) -> str:
    """
    Return a database url with a unique database name.
    If _get_connection_url() returns a value, the database is postgresql; otherwise, it's
    sqlite (referring to a location witin the /tmp directory).
    """
    # TODO this duplication should be removed (see url_factory).
    database = _generate_unique_database_name()
    connection_url = _get_connection_url()
    if connection_url:
        return _make_postgres_db_url(DbUrl(connection_url), database)
    else:
        return _make_sqlite_db_url(tmp_directory, database)


def initialize_model(mapper_registry, engine):
    mapper_registry.metadata.create_all(engine)


def replace_database_in_url(url, database_name):
    """
    Substitute the database part of url for database_name.

    Example: replace_database_in_url('foo/db1', 'db2') returns 'foo/db2'
    This will not work for unix domain connections.
    """
    i = url.rfind("/")
    return f"{url[:i]}/{database_name}"


def drop_database(db_url, database):
    """Drop database; connect with db_url.

    Used only for test purposes to cleanup after creating a test database.
    """
    if _is_postgres(db_url) or _is_mysql(db_url):
        _drop_database(db_url, database)
    else:
        url = make_url(db_url)
        os.remove(url.database)


def dbcleanup_wrapper(session, obj, where_clause=None):
    with dbcleanup(session, obj, where_clause):
        yield obj


@contextmanager
def dbcleanup(session, obj, where_clause=None):
    """
    Use the session to store obj in database; delete from database on exit, bypassing the session.

    If obj does not have an id field, a SQLAlchemy WHERE clause should be provided to construct
    a custom select statement.
    """
    return_id = where_clause is None

    try:
        obj_id = persist(session, obj, return_id)
        yield obj_id
    finally:
        table = obj.__table__
        if where_clause is None:
            where_clause = _get_default_where_clause(type(obj), obj_id)
        stmt = delete(table).where(where_clause)
        session.execute(stmt)


def persist(session, obj, return_id=True):
    """
    Use the session to store obj in database, then remove obj from session,
    so that on a subsequent load from the database we get a clean instance.
    """
    session.add(obj)
    session.flush()
    obj_id = obj.id if return_id else None  # save this before obj is expunged
    session.expunge(obj)
    return obj_id


def delete_from_database(session, objects):
    """
    Delete each object in objects from database.
    May be called at the end of a test if use of a context manager is impractical.
    (Assume all objects have the id field as their primary key.)
    """
    # Ensure we have a list of objects (check for list explicitly: a model can be iterable)
    if not isinstance(objects, list):
        objects = [objects]

    for obj in objects:
        table = obj.__table__
        stmt = delete(table).where(table.c.id == obj.id)
        session.execute(stmt)


def get_stored_obj(session, cls, obj_id=None, where_clause=None, unique=False):
    # Either obj_id or where_clause must be provided, but not both
    assert bool(obj_id) ^ (where_clause is not None)
    if where_clause is None:
        where_clause = _get_default_where_clause(cls, obj_id)
    stmt = select(cls).where(where_clause)
    result = session.execute(stmt)
    # unique() is required if result contains joint eager loads against collections
    # https://gerrit.sqlalchemy.org/c/sqlalchemy/sqlalchemy/+/2253
    if unique:
        result = result.unique()
    return result.scalar_one()


def get_stored_instance_by_id(session, cls_, id):
    statement = select(cls_).where(cls_.__table__.c.id == id)
    return session.execute(statement).scalar_one()


def _is_postgres(url: DbUrl) -> bool:
    return url.startswith("postgres")


def _is_mysql(url: DbUrl) -> bool:
    return url.startswith("mysql")


def _drop_postgres_database(url: DbUrl) -> None:
    db_url = make_url(url)
    database = db_url.database
    connection_url = db_url.set(database="postgres")
    _drop_database(connection_url, database)


def _drop_database(connection_url, database_name):
    engine = create_engine(connection_url, isolation_level="AUTOCOMMIT")
    preparer = IdentifierPreparer(engine.dialect)
    database_name = preparer.quote(database_name)
    stmt = f"DROP DATABASE IF EXISTS {database_name}"
    with engine.connect() as conn:
        conn.execute(stmt)
    engine.dispose()


def _get_default_where_clause(cls, obj_id):
    where_clause = cls.__table__.c.id == obj_id
    return where_clause


def _generate_unique_database_name() -> str:
    return f"galaxytest_{uuid.uuid4().hex}"


def _get_connection_url() -> Optional[str]:
    return os.environ.get("GALAXY_TEST_DBURI")


def _make_sqlite_db_url(tmpdir: str, database: str) -> DbUrl:
    path = os.path.join(tmpdir, database)
    return DbUrl(f"sqlite:///{path}")


def _make_postgres_db_url(connection_url: DbUrl, database: str) -> DbUrl:
    url = make_url(connection_url)
    url = url.set(database=database)
    return DbUrl(str(url))
