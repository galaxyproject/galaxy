""" Test Tool testing logic.

I am going to migrate from using galaxy.tools.parameters and Galaxy Tool internals to
tool sources and I want to ensure the results do not change.
"""

from typing import (
    Any,
    List,
)

from galaxy.app_unittest_utils import tools_support
from galaxy.tool_util.unittest_utils import functional_test_tool_path
from galaxy.tools.test import parse_tests
from galaxy.util.unittest import TestCase

# Not the whole response, just some keys and such to test...
SIMPLE_CONSTRUCTS_EXPECTATIONS = [
    (["inputs", "p1|p1use"], [True]),
    (["inputs", "booltest"], [True]),
    (["inputs", "inttest"], ["12456"]),
    (["inputs", "files_0|file"], ["simple_line.txt"]),
    (["outputs", 0, "name"], "out_file1"),
]


class TestTestParsing(TestCase, tools_support.UsesTools):
    tool_action: "MockAction"

    def setUp(self):
        self.setup_app()

    def tearDown(self):
        self.tear_down_app()

    def test_state_parsing(self):
        self._init_tool_for_path(functional_test_tool_path("simple_constructs.xml"))
        test_dicts = parse_tests(self.tool, self.tool_source)
        self._verify_each(test_dicts[0].to_dict(), SIMPLE_CONSTRUCTS_EXPECTATIONS)
        print(test_dicts[0].to_dict())
        assert False

    def _verify_each(self, target_dict: dict, expectations: List[Any]):
        for path, expectation in expectations:
            self._verify(target_dict, path, expectation)

    def _verify(self, target_dict: dict, expectation_path: List[str], expectation: Any):
        rest = target_dict
        for path_part in expectation_path:
            rest = rest[path_part]
        assert rest == expectation
