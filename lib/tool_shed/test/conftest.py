import os

import pytest

from galaxy_test.conftest import (  # noqa: F401
    embedded_driver,
    real_driver,
)
from tool_shed.test.base import driver


@pytest.fixture(scope="session")
def tool_shed_test_driver():
    if not os.environ.get("GALAXY_TEST_ENVIRONMENT_CONFIGURED"):
        ts_driver = driver.ToolShedTestDriver()
        ts_driver.setup()
        try:
            yield ts_driver
        finally:
            ts_driver.tear_down()
