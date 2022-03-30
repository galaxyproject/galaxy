import os

import pytest
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
