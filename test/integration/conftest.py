import tempfile

import pytest

from galaxy_test.conftest import pytest_configure  # noqa: F401


@pytest.fixture(scope="session")
def celery_includes():
    return ["galaxy.celery.tasks"]


def pytest_collection_finish(session):
    try:
        # This needs to be run after test collection
        from .test_config_defaults import DRIVER

        DRIVER.tear_down()
        print("Galaxy test driver shutdown successful")
    except Exception:
        pass


@pytest.fixture
def temp_file():
    with tempfile.NamedTemporaryFile(delete=True, mode="wb") as fh:
        yield fh
