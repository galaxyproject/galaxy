import os
from typing import Any

import pytest

from galaxy_test.base.api import UsesCeleryTasks
from galaxy_test.driver.driver_util import GalaxyTestDriver
from galaxy_test.driver.pytest import (  # noqa: F401
    celery_includes,
    embedded_driver,
    pytest_configure,
    pytest_plugins,
    test_http_server,
)


class ConfigObject:
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config: dict[str, Any]) -> None:
        UsesCeleryTasks.handle_galaxy_config_kwds(config)


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
