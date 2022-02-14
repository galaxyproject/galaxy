import os
import tempfile

import pytest

try:
    import psycopg2
except ImportError:
    psycopg2 = None

from galaxy.app_unittest_utils import galaxy_mock
from galaxy.util import which


def create_base_test(connection, amqp_type, amqp_connection=None):
    app = galaxy_mock.MockApp(database_connection=connection)
    app.config.database_connection = connection
    app.config.amqp_internal_connection = amqp_connection or "sqlalchemy+%s" % app.config.database_connection
    app.amqp_type = amqp_type
    return app


@pytest.fixture()
def sqlite_connection(request):
    with tempfile.NamedTemporaryFile() as temp:
        yield f"sqlite:////{temp.name}"


@pytest.fixture()
def sqlite_rabbitmq_app(sqlite_connection):
    def create_app():
        amqp_connection = os.environ.get("GALAXY_TEST_AMQP_INTERNAL_CONNECTION")
        return create_base_test(sqlite_connection, amqp_type="rabbitmq", amqp_connection=amqp_connection)

    return create_app


@pytest.fixture()
def sqlite_app(sqlite_connection):
    def create_app():
        return create_base_test(sqlite_connection, amqp_type="sqlite")

    return create_app


@pytest.fixture()
def postgres_app(postgresql_proc):
    connection = "postgresql://{p.user}@{p.host}:{p.port}/".format(p=postgresql_proc)

    def create_app():
        return create_base_test(connection, amqp_type="postgres")

    return create_app


@pytest.fixture(params=["postgres_app", "sqlite_app", "sqlite_rabbitmq_app"])
def database_app(request):
    if request.param == "postgres_app":
        if not which("initdb"):
            pytest.skip("initdb must be on PATH for postgresql fixture")
        if not psycopg2:
            pytest.skip("psycopg2 must be installed for postgresql fixture")
    if request.param == "sqlite_rabbitmq_app":
        if not os.environ.get("GALAXY_TEST_AMQP_INTERNAL_CONNECTION"):
            pytest.skip("rabbitmq tests will be skipped if GALAXY_TEST_AMQP_INTERNAL_CONNECTION env var is unset")
    return request.getfixturevalue(request.param)
