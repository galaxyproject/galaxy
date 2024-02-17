import os

import pytest

from galaxy_test.driver.driver_util import GalaxyTestDriver
from galaxy_test.selenium.framework import SeleniumTestCase


@pytest.fixture(scope="session")
def real_driver():
    if not os.environ.get("GALAXY_TEST_ENVIRONMENT_CONFIGURED"):
        driver = GalaxyTestDriver()
        driver.setup(SeleniumTestCase)
        try:
            yield driver
        finally:
            driver.tear_down()
    else:
        yield None


@pytest.fixture(scope="class")
def embedded_driver(real_driver, request):
    request.cls._test_driver = real_driver
