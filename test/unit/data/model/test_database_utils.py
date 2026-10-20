import os
import tempfile

from sqlalchemy import text
from sqlalchemy.engine import Engine

from galaxy.model.database_utils import (
    create_database,
    database_exists,
    supports_returning,
)
from galaxy.model.unittest_utils.model_testing_utils import (
    disposing_engine,
    drop_database,
    replace_database_in_url,
    skip_if_not_mysql_uri,
    skip_if_not_postgres_uri,
)


@skip_if_not_postgres_uri
def test_create_exists_postgres_database(database_name, postgres_url):
    assert not database_exists(postgres_url, database_name)
    create_database(postgres_url, database_name)
    assert database_exists(postgres_url, database_name)
    drop_database(postgres_url, database_name)
    assert not database_exists(postgres_url, database_name)


@skip_if_not_postgres_uri
def test_create_exists_postgres_database__pass_as_url(database_name, postgres_url):
    # the database in the url is the one to create/check
    url = replace_database_in_url(postgres_url, database_name)

    assert not database_exists(url)
    create_database(url)
    assert database_exists(url)
    drop_database(postgres_url, database_name)
    assert not database_exists(url)


def test_create_exists_sqlite_database(database_name):
    with tempfile.TemporaryDirectory() as tmp_dir:
        url = make_sqlite_url(tmp_dir, database_name)

        assert not database_exists(url, database_name)
        create_database(url, database_name)
        assert database_exists(url, database_name)
        drop_database(url, database_name)
        assert not database_exists(url, database_name)


def test_create_exists_sqlite_database__pass_as_url(database_name):
    # the database in the url is the one to create/check
    with tempfile.TemporaryDirectory() as tmp_dir:
        url = make_sqlite_url(tmp_dir, database_name)

        assert not database_exists(url)
        create_database(url)
        assert database_exists(url)
        drop_database(url, database_name)
        assert not database_exists(url)


def test_exists_sqlite_in_memory_database(database_name, sqlite_memory_url):
    assert database_exists(sqlite_memory_url)


@skip_if_not_mysql_uri
def test_create_exists_mysql_database(database_name, mysql_url):
    assert not database_exists(mysql_url, database_name)
    create_database(mysql_url, database_name)
    assert database_exists(mysql_url, database_name)
    drop_database(mysql_url, database_name)
    assert not database_exists(mysql_url, database_name)


def test_supports_returning_sqlite(database_name):
    with tempfile.TemporaryDirectory() as tmp_dir:
        url = make_sqlite_url(tmp_dir, database_name)
        with disposing_engine(url) as engine:
            assert_supports_returning(engine)


@skip_if_not_postgres_uri
def test_supports_returning_postgres(database_name, postgres_url):
    url = replace_database_in_url(postgres_url, database_name)
    create_database(url)
    try:
        with disposing_engine(url) as engine:
            assert_supports_returning(engine)
    finally:
        drop_database(postgres_url, database_name)


def assert_supports_returning(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE job (id INTEGER PRIMARY KEY, tool_id VARCHAR(255))"))
    supports_returning.cache_clear()
    assert supports_returning(engine) is True


def make_sqlite_url(tmp_dir, database_name):
    path = os.path.join(tmp_dir, database_name)
    return f"sqlite:///{path}"
