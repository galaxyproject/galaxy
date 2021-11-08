import os
import tempfile
import uuid

import pytest


pytest_plugins = [
    'unit.data.model.migrations.fixtures.schemas',
    'unit.data.model.migrations.fixtures.tables',
]


@pytest.fixture(scope='module')
def tmp_directory():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def url_factory(tmp_directory):
    """Return factory producing unique sqlalchemy db-urls within tmp_directory."""
    def url():
        database_file = f'galaxytest_{uuid.uuid4().hex}'
        path = os.path.join(tmp_directory, database_file)
        return f'sqlite:///{path}'
    return url
