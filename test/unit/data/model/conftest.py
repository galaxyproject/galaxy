import os
import uuid

import pytest


@pytest.fixture
def database_name():
    return f"galaxytest_{uuid.uuid4().hex}"


@pytest.fixture
def postgres_url():
    return os.environ.get("GALAXY_TEST_CONNECT_POSTGRES_URI")


@pytest.fixture
def mysql_url():
    return os.environ.get("GALAXY_TEST_CONNECT_MYSQL_URI")


@pytest.fixture
def sqlite_memory_url():
    return "sqlite:///:memory:"
