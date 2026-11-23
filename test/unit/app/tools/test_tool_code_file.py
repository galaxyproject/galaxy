import pytest

from galaxy.app_unittest_utils import tools_support
from galaxy.util.unittest import TestCase

TOOL_CONTENTS = """<tool id="$tool_id" name="code file tool" version="1.0.0">
    <code file="operation_filter.py" />
    <command>echo</command>
    <inputs>
        <param name="input1" type="data" format="interval" label="First" />
    </inputs>
    <outputs>
        <data name="output" format="interval" />
    </outputs>
</tool>
"""

PYTHON2_CODE_FILE = """
def validate_input(trans, error_map, param_values, page_param_map):
    for name, param in page_param_map.iteritems():
        error_map[name] = "validated"
"""


class TestToolCodeFile(TestCase, tools_support.UsesTools):
    def setUp(self):
        super().setUp()
        self.setup_app()

    def tearDown(self):
        self.tear_down_app()

    def _validate_input(self, tool_id):
        tool = self._init_tool(
            TOOL_CONTENTS,
            tool_id=tool_id,
            extra_file_contents=PYTHON2_CODE_FILE,
            extra_file_path="operation_filter.py",
        )
        error_map: dict[str, str] = {}
        tool.get_hook("validate_input")(None, error_map, {}, tool.inputs)
        return error_map

    def test_listed_tool_code_file_is_translated(self):
        assert self._validate_input("gops_intersect_1") == {"input1": "validated"}

    def test_unlisted_tool_code_file_is_not_translated(self):
        with pytest.raises(AttributeError, match="iteritems"):
            self._validate_input("unlisted_tool")
