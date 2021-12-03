import tempfile

import pytest

from galaxy_test.api.conftest import pytest_configure  # noqa: F401


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
    with tempfile.NamedTemporaryFile(delete=True, mode='wb') as fh:
        yield fh
