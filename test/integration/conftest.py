import tempfile

import pytest

from galaxy_test.conftest import (  # noqa: F401
    pytest_configure,
    pytest_plugins,
)


@pytest.fixture(scope="session")
def celery_includes():
    return ["galaxy.celery.tasks"]


@pytest.fixture
def temp_file():
    with tempfile.NamedTemporaryFile(delete=True, mode="wb") as fh:
        yield fh
