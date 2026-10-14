import os

import pytest

from galaxy_test.api.conftest import embedded_driver  # noqa: F401
from galaxy_test.driver.driver_util import GalaxyTestDriver
from galaxy_test.driver.pytest import (  # noqa: F401
    celery_includes,
    pytest_configure,
    pytest_plugins,
    test_http_server,
)


class ConfigObject:
    framework_tool_and_types = True


@pytest.fixture(scope="session")
def real_driver():
    if not os.environ.get("GALAXY_TEST_ENVIRONMENT_CONFIGURED"):
        driver = GalaxyTestDriver()
        driver.setup(ConfigObject)
        try:
            yield driver
        finally:
            driver.tear_down()
    else:
        yield None
