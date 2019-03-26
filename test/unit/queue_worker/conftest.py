import contextlib
import os
import tempfile

import pytest

from galaxy.util import which
from ..unittest_utils import galaxy_mock


@contextlib.contextmanager
def create_base_test(connection, amqp_connection=None):
    app = galaxy_mock.MockApp(database_connection=connection)
    app.config.database_connection = connection
    app.config.amqp_internal_connection = amqp_connection or "sqlalchemy+%s" % app.config.database_connection
    yield app


@pytest.fixture()
def sqlite_connection():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield 'sqlite:////%s' % path
    os.remove(path)


@pytest.fixture()
def sqlite_rabbitmq_app(sqlite_connection):

    def create_app():
        with create_base_test(sqlite_connection, amqp_connection='amqp://127.0.0.1:5672/') as app:
            return app

    return create_app


@pytest.fixture()
def sqlite_app(sqlite_connection):

    def create_app():
        with create_base_test(sqlite_connection) as app:
            return app

    return create_app


@pytest.fixture()
def postgres_app(postgresql_proc):
    connection = "postgresql://{p.user}@{p.host}:{p.port}/".format(p=postgresql_proc)

    def create_app():
        with create_base_test(connection) as app:
            return app

    return create_app


@pytest.fixture(params=['postgres_app', 'sqlite_app', 'sqlite_rabbitmq_app'])
def database_app(request):
    if request.param == 'postgres_app':
        if not which('initdb'):
            pytest.skip("initdb must be on PATH for postgresql fixture")
    yield request.getfixturevalue(request.param)
