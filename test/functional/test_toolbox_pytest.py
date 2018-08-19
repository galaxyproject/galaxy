import os
import sys

galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir + '/' + os.path.pardir))
sys.path[1:1] = [os.path.join(galaxy_root, "lib"), os.path.join(galaxy_root, "test")]

from base import driver_util

TEST_PREFIX = 'TestForTool_'


class DefaultGalaxyTestDriver(driver_util.GalaxyTestDriver):
    """Default Galaxy-style nose test driver.

    Just populate non-shed tool tests and run tests. Works
    for tool tests, regular twill tests, and API testing.
    """

    def build_tests(self):
        """Build framework tool test methods."""
        return self.build_tool_tests(return_test_classes=True)


def __generate_testcases():
    driver = DefaultGalaxyTestDriver()
    driver.setup()
    tests = driver.build_tests()
    for test_name, test_class in tests.items():
        if test_name.startswith(TEST_PREFIX):
            yield (test_name[len(TEST_PREFIX):], test_class)
    driver.tear_down()


def idfn(val):
    return val[0]


def pytest_generate_tests(metafunc):
    if 'tool_test' in metafunc.fixturenames:
        metafunc.parametrize("tool_test", __generate_testcases(), ids=idfn)


def test_tool(tool_test):
    test = tool_test[1]
    test.do_it(test)
