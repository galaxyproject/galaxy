import os
import tempfile

import pytest

from galaxy.util import which
from ..unittest_utils import galaxy_mock


def create_base_test(connection, amqp_type, amqp_connection=None):
    app = galaxy_mock.MockApp(database_connection=connection)
    app.config.database_connection = connection
    app.config.amqp_internal_connection = amqp_connection or "sqlalchemy+%s" % app.config.database_connection
    app.amqp_type = amqp_type
    return app


@pytest.fixture()
def sqlite_connection(request):
    fd, path = tempfile.mkstemp()
    os.close(fd)
    request.addfinalizer(lambda: os.remove(path))
    return 'sqlite:////%s' % path


@pytest.fixture()
def sqlite_rabbitmq_app(sqlite_connection):

    def create_app():
        return create_base_test(sqlite_connection, amqp_type='rabbitmq', amqp_connection='amqp://guest:guest@localhost:5672/')

    return create_app


@pytest.fixture()
def sqlite_app(sqlite_connection):

    def create_app():
        return create_base_test(sqlite_connection, amqp_type='sqlite')

    return create_app


@pytest.fixture()
def postgres_app(postgresql_proc):
    connection = "postgresql://{p.user}@{p.host}:{p.port}/".format(p=postgresql_proc)

    def create_app():
        return create_base_test(connection, amqp_type='postgres')

    return create_app


@pytest.fixture(params=['postgres_app', 'sqlite_app', 'sqlite_rabbitmq_app'])
def database_app(request):
    if request.param == 'postgres_app':
        if not which('initdb'):
            pytest.skip("initdb must be on PATH for postgresql fixture")
    return request.getfixturevalue(request.param)
