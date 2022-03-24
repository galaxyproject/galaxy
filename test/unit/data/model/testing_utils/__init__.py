import os
from contextlib import contextmanager

import pytest
from sqlalchemy import (
    delete,
    select,
)
from sqlalchemy.engine.url import make_url
from sqlalchemy.sql.compiler import IdentifierPreparer

from galaxy.model.database_utils import sqlalchemy_engine

# GALAXY_TEST_CONNECT_POSTGRES_URI='postgresql://postgres@localhost:5432/postgres' pytest test/unit/model
skip_if_not_postgres_uri = pytest.mark.skipif(
    not os.environ.get("GALAXY_TEST_CONNECT_POSTGRES_URI"), reason="GALAXY_TEST_CONNECT_POSTGRES_URI not set"
)

# GALAXY_TEST_CONNECT_MYSQL_URI='mysql+mysqldb://root@localhost/mysql' pytest test/unit/model
skip_if_not_mysql_uri = pytest.mark.skipif(
    not os.environ.get("GALAXY_TEST_CONNECT_MYSQL_URI"), reason="GALAXY_TEST_CONNECT_MYSQL_URI not set"
)


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
    if db_url.startswith("postgresql") or db_url.startswith("mysql"):
        with sqlalchemy_engine(db_url) as engine:
            preparer = IdentifierPreparer(engine.dialect)
            database = preparer.quote(database)
            stmt = f"DROP DATABASE IF EXISTS {database}"
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(stmt)
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


def _get_default_where_clause(cls, obj_id):
    where_clause = cls.__table__.c.id == obj_id
    return where_clause
