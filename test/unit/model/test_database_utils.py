import os
import tempfile
import uuid

import pytest

from galaxy.model.database_utils import (
    create_database,
    database_exists,
)
from ..unittest_utils.database_helpers import drop_database


# GALAXY_TEST_CONNECT_POSTGRES_URI='postgresql://postgres@localhost:5432/postgres' pytest test/unit/util/test_database.py
skip_if_not_postgres_uri = pytest.mark.skipif(
    not os.environ.get('GALAXY_TEST_CONNECT_POSTGRES_URI'),
    reason="GALAXY_TEST_CONNECT_POSTGRES_URI not set"
)


@pytest.fixture
def database_name():
    return f'galaxytest_{uuid.uuid4().hex}'


@pytest.fixture
def postgres_url():
    return os.environ.get('GALAXY_TEST_CONNECT_POSTGRES_URI')


@pytest.fixture
def sqlite_memory_url():
    return 'sqlite:///:memory:'


@skip_if_not_postgres_uri
def test_postgres_create_exists_drop_database(database_name, postgres_url):
    assert not database_exists(postgres_url, database_name)
    create_database(postgres_url, database_name)
    assert database_exists(postgres_url, database_name)
    drop_database(postgres_url, database_name)
    assert not database_exists(postgres_url, database_name)


@skip_if_not_postgres_uri
def test_postgres_create_exists_drop_database__pass_one_argument(database_name, postgres_url):
    # Substitute the database part of postgres_url for database_name:
    # url: 'foo/db1', database: 'db2' => url: 'foo/db2' (will not work for unix domain connections)
    url = postgres_url
    i = url.rfind('/')
    url = f'{url[:i]}/{database_name}'

    assert not database_exists(url)
    create_database(url)
    assert database_exists(url)
    drop_database(postgres_url, database_name)
    assert not database_exists(url)


def test_sqlite_create_exists_drop_database(database_name):
    with tempfile.TemporaryDirectory() as tmp_dir:
        url = _make_sqlite_url(tmp_dir, database_name)

        assert not database_exists(url, database_name)
        create_database(url, database_name)
        assert database_exists(url, database_name)
        drop_database(url, database_name)
        assert not database_exists(url, database_name)


def test_sqlite_create_exists_drop_database__pass_one_argument(database_name):
    with tempfile.TemporaryDirectory() as tmp_dir:
        url = _make_sqlite_url(tmp_dir, database_name)

        assert not database_exists(url)
        create_database(url)
        assert database_exists(url)
        drop_database(url, database_name)
        assert not database_exists(url)


def test_sqlite_create_exists_drop_in_memory_database(database_name, sqlite_memory_url):
    assert database_exists(sqlite_memory_url)


def _make_sqlite_url(tmp_dir, database_name):
    path = os.path.join(tmp_dir, database_name)
    return f'sqlite:///{path}?isolation_level=IMMEDIATE'
