#!/usr/bin/env python
"""Test driver for many Galaxy Python functional tests.

Launch this script by running ``run_tests.sh`` from GALAXY_ROOT, see
that script for a list of options.
"""

import os
import os.path
import sys

galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
sys.path[1:1] = [os.path.join(galaxy_root, "lib"), os.path.join(galaxy_root, "test")]

from base import driver_util
from base.api_util import get_master_api_key, get_user_api_key

log = driver_util.build_logger()


class MigratedToolsGalaxyTestDriver(driver_util.GalaxyTestDriver):
    """Instantiate a Galaxy-style nose TestDriver for testing migrated Galaxy tools."""

    testing_shed_tools = True

    def build_tests(self):
        """Build migrated tool test methods."""
        self.setup_shed_tools(
            testing_migrated_tools=True,
        )
        self.build_tool_tests()


class InstalledToolsGalaxyTestDriver(driver_util.GalaxyTestDriver):
    """Galaxy-style nose TestDriver for testing installed Galaxy tools."""

    testing_shed_tools = True

    def build_tests(self):
        """Build installed tool test methods."""
        self.setup_shed_tools(
            testing_installed_tools=True,
        )
        self.build_tool_tests()


class DefaultGalaxyTestDriver(driver_util.GalaxyTestDriver):
    """Default Galaxy-style nose test driver.

    Just populate non-shed tool tests and run tests. Works
    for tool tests, regular twill tests, and API testing.
    """

    def build_tests(self):
        """Build framework tool test methods."""
        self.build_tool_tests()


class SeleniumGalaxyTestDriver(driver_util.GalaxyTestDriver):
    """Galaxy-style nose TestDriver for selenium framework testing."""

    framework_tool_and_types = True

    @driver_util.classproperty
    def default_web_host(cls):
        from selenium_tests.framework import default_web_host_for_selenium_tests
        return default_web_host_for_selenium_tests()


class FrameworkToolsGalaxyTestDriver(DefaultGalaxyTestDriver):
    """Galaxy-style nose TestDriver for testing framework Galaxy tools."""

    framework_tool_and_types = True
    conda_auto_init = True
    conda_auto_install = True


class DataManagersGalaxyTestDriver(driver_util.GalaxyTestDriver):
    """Galaxy-style nose TestDriver for testing framework Galaxy tools."""

    def build_tests(self):
        """Build data manager test methods."""
        import functional.test_data_managers
        functional.test_data_managers.data_managers = self.app.data_managers
        functional.test_data_managers.build_tests(
            tmp_dir=self.galaxy_test_tmp_dir,
            testing_shed_tools=self.testing_shed_tools,
            master_api_key=get_master_api_key(),
            user_api_key=get_user_api_key(),
            user_email=self.app.config.admin_users_list[0],
            create_admin=True,
        )


TEST_DRIVERS = {
    '-migrated': MigratedToolsGalaxyTestDriver,
    '-installed': InstalledToolsGalaxyTestDriver,
    '-framework': FrameworkToolsGalaxyTestDriver,
    '-data_managers': DataManagersGalaxyTestDriver,
    '-selenium': SeleniumGalaxyTestDriver,
}


def find_test_driver():
    """Look at command-line args and find the correct Galaxy test driver."""
    test_driver = DefaultGalaxyTestDriver

    for key in TEST_DRIVERS.keys():
        if _check_arg(key):
            test_driver = TEST_DRIVERS[key]

    return test_driver


def _check_arg(name):
    try:
        index = sys.argv.index(name)
        del sys.argv[index]
        ret_val = True
    except ValueError:
        ret_val = False
    return ret_val


if __name__ == "__main__":
    driver_util.drive_test(find_test_driver())
