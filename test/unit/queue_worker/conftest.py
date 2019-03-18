import contextlib
import os
import tempfile

import pytest

from galaxy.util import which
from ..unittest_utils import galaxy_mock


@contextlib.contextmanager
def create_base_test(connection):
    app = galaxy_mock.MockApp(database_connection=connection)
    app.config.database_connection = connection
    yield app


@pytest.fixture(scope='session')
def sqlite_connection():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield 'sqlite:////%s' % path
    os.remove(path)


@pytest.fixture(scope='session')
def sqlite_app(sqlite_connection):
    with create_base_test(sqlite_connection) as app:
        yield app


@pytest.fixture(scope='session')
def postgres_app(postgresql_proc):
    connection = "postgresql://{p.user}@{p.host}:{p.port}/".format(p=postgresql_proc)
    with create_base_test(connection) as app:
        yield app


@pytest.fixture(params=['postgres_app', 'sqlite_app'], scope='session')
def database_app(request):
    if request.param == 'postgres_app':
        if not which('initdb'):
            pytest.skip("initdb must be on PATH for postgresql fixture")
    yield request.getfixturevalue(request.param)
