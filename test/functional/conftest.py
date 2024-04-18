import os

import pytest

from galaxy_test.conftest import pytest_plugins  # noqa: F401
from galaxy_test.driver.driver_util import GalaxyTestDriver
from .test_toolbox_pytest import TestFrameworkTools


@pytest.fixture(scope="session", autouse=True)
def celery_includes():
    yield ["galaxy.celery.tasks"]


@pytest.fixture(scope="session")
def real_driver():
    if not os.environ.get("GALAXY_TEST_ENVIRONMENT_CONFIGURED"):
        driver = GalaxyTestDriver()
        driver.setup(TestFrameworkTools)
        try:
            yield driver
        finally:
            driver.tear_down()
    else:
        yield None


@pytest.fixture(scope="class")
def embedded_driver(real_driver, request):
    request.cls._test_driver = real_driver
