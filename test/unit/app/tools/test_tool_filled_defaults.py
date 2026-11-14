from galaxy.app_unittest_utils import tools_support
from galaxy.app_unittest_utils.galaxy_mock import MockTrans
from galaxy.model import History
from galaxy.tools.parameters.workflow_utils import RuntimeValue
from galaxy.util.unittest import TestCase

TOOL_CONTENTS = """<tool id="filled_defaults" name="filled_defaults" version="1.0">
    <command>echo</command>
    <inputs>
        <param name="input" type="data" format="txt" label="from" />
        <param name="num_lines" type="integer" value="1" label="Randomly select" />
        <param name="title" type="text" optional="true" label="Title" />
        <param name="choice" type="select" label="Choice" />
    </inputs>
    <outputs>
        <data name="out" format="txt" />
    </outputs>
</tool>
"""


class TestFilledDefaults(TestCase, tools_support.UsesTools):
    def setUp(self):
        super().setUp()
        self.setup_app()
        self._init_tool(TOOL_CONTENTS)
        self.trans = MockTrans(self.app, history=History())

    def tearDown(self):
        self.tear_down_app()

    def _check(self, values):
        filled_defaults: dict[str, str] = {}
        messages = self.tool.check_and_update_param_values(
            values, self.trans, workflow_building_mode=True, filled_defaults=filled_defaults
        )
        return filled_defaults, messages

    def test_missing_values_with_a_default_are_filled_defaults(self):
        filled_defaults, messages = self._check({})
        assert filled_defaults == {
            "input": "Default for 'from': a value set at runtime.",
            "num_lines": "Default for 'Randomly select': '1'.",
            "title": "Default for 'Title': no value.",
        }
        # a required select without options has no default to fill in
        assert list(messages) == ["choice"]

    def test_replaced_values_stay_upgrade_messages(self):
        filled_defaults, messages = self._check(
            {"input": RuntimeValue(), "num_lines": "not-a-number", "title": "", "choice": None}
        )
        assert "num_lines" not in filled_defaults
        assert messages["num_lines"].endswith("Using default: '1'.")
