import os
import sys

galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir + '/' + os.path.pardir))
sys.path[1:1] = [os.path.join(galaxy_root, "lib"), os.path.join(galaxy_root, "test")]

import pytest
from base import driver_util

SKIPTEST = os.path.join(os.path.dirname(__file__), 'known_broken_tools.txt')
TEST_PREFIX = 'TestForTool_'


class DefaultGalaxyTestDriver(driver_util.GalaxyTestDriver):
    """Default Galaxy-style nose test driver.

    Just populate non-shed tool tests and run tests. Works
    for tool tests, regular twill tests, and API testing.
    """
    conda_auto_init = True
    conda_auto_install = True

    def build_tests(self):
        """Build framework tool test methods."""
        return self.build_tool_tests(return_test_classes=True)


def get_skiplist():
    with open(SKIPTEST) as skiptest:
        skiplist = [l.strip() for l in skiptest if l.strip() and not l.startswith('#')]
        return skiplist


def galaxy_driver():
    driver = DefaultGalaxyTestDriver()
    driver.setup()
    return driver


@pytest.fixture(scope='module')
def driver(request):
    request.addfinalizer(DRIVER.tear_down)
    return DRIVER


def get_cases():
    # We setup a global driver, so that the driver fixture can tear down the driver
    # Ideally `galaxy_driver` or `cases` would be fixtures and clean up after the yield,
    # but that's not compatible with the use use of pytest.mark.parametrize
    global DRIVER
    DRIVER = galaxy_driver()
    tests = DRIVER.build_tests()
    cases = []
    for test_name, test_class in tests.items():
        if test_name.startswith(TEST_PREFIX):
            test_class.runTest = lambda : None
            test_instance = test_class()
            cases.append(test_instance)
    return cases


def cases():
    skiplist = get_skiplist()
    for test_instance in get_cases():
        for index in range(test_instance.test_count):
            test = (test_instance.tool_id + "_test_%d" % (index + 1), test_instance, index)
            marks = []
            marks.append(pytest.mark.skipif(test_instance.tool_id in skiplist, reason="tool in skiplist"))
            if 'data_manager_' in test_instance.tool_id:
                marks.append(pytest.mark.data_manager(test))
            else:
                marks.append(pytest.mark.tool(test))
            yield pytest.param(test, marks=marks)


def idfn(val):
    return val[0]


@pytest.mark.parametrize("testcases", cases(), ids=idfn)
def test_tool(testcases, driver):
    test = testcases[1]
    test.do_it(test_index=testcases[2])
