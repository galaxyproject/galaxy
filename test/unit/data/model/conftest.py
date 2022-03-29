import os
import tempfile
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


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


@pytest.fixture(scope="module")
def engine():
    db_uri = "sqlite:///:memory:"
    return create_engine(db_uri)


@pytest.fixture
def session(init_model, engine):
    with Session(engine) as s:
        yield s


@pytest.fixture(scope="module")
def tmp_directory():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir
