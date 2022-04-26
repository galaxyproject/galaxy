import os
import tempfile

from galaxy.model.database_utils import (
    create_database,
    database_exists,
)
from .testing_utils import (
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


def make_sqlite_url(tmp_dir, database_name):
    path = os.path.join(tmp_dir, database_name)
    return f"sqlite:///{path}"
