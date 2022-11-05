import os

import pytest

try:
    from galaxy_test.driver.driver_util import GalaxyTestDriver
except ImportError:
    # Galaxy libraries and galaxy test driver not available, just assume we're
    # targetting a remote Galaxy.
    GalaxyTestDriver = None  # type: ignore[misc,assignment]


@pytest.fixture(scope="session")
def galaxy_test_driver():
    if not os.environ.get("GALAXY_TEST_ENVIRONMENT_CONFIGURED"):
        driver = GalaxyTestDriver()
        driver.setup()
        try:
            yield driver
        finally:
            driver.tear_down()
