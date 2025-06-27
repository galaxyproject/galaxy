import os
from typing import (
    cast,
    List,
    NamedTuple,
)

import pytest

from galaxy.tool_util.verify.interactor import (
    DEFAULT_USE_LEGACY_API,
    UseLegacyApiT,
)
from galaxy_test.api._framework import ApiTestCase
from galaxy_test.driver.driver_util import GalaxyTestDriver

SKIPTEST = os.path.join(os.path.dirname(__file__), "known_broken_tools.txt")


class ToolTest(NamedTuple):
    tool_id: str
    tool_version: str
    test_index: int


def get_skiplist():
    with open(SKIPTEST) as skiptest:
        skiplist = [line.strip() for line in skiptest if line.strip() and not line.startswith("#")]
        return skiplist


def get_cases() -> List[ToolTest]:
    atc = ApiTestCase()
    atc._test_driver = GalaxyTestDriver()
    atc._test_driver.setup()
    atc.setUp()
    test_summary = atc.galaxy_interactor.get_tests_summary()
    test_cases = []
    for tool_id, summary_dict in test_summary.items():
        for tool_version, tool_dict in summary_dict.items():
            for index in range(tool_dict["count"]):
                test_cases.append(ToolTest(tool_id, tool_version, index))
    atc._test_driver.stop_servers()
    return test_cases


def cases():
    skiplist = get_skiplist()
    for tool_test in get_cases():
        marks = []
        marks.append(pytest.mark.skipif(tool_test.tool_id in skiplist, reason="tool in skiplist"))
        if "data_manager_" in tool_test.tool_id:
            marks.append(pytest.mark.data_manager(tool_test))
        else:
            marks.append(pytest.mark.tool(tool_test))
        yield pytest.param(tool_test, marks=marks)


def idfn(val: ToolTest):
    return f"{val.tool_id}/{val.tool_version}-{val.test_index}"


class TestFrameworkTools(ApiTestCase):
    conda_auto_init = True
    conda_auto_install = True

    @pytest.mark.parametrize("testcase", cases(), ids=idfn)
    def test_tool(self, testcase: ToolTest):
        use_legacy_api = cast(UseLegacyApiT, os.environ.get("GALAXY_TEST_USE_LEGACY_TOOL_API", DEFAULT_USE_LEGACY_API))
        self._test_driver.run_tool_test(
            testcase.tool_id, testcase.test_index, tool_version=testcase.tool_version, use_legacy_api=use_legacy_api
        )
