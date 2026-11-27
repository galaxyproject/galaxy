import json
from copy import deepcopy
from typing import cast
from unittest import mock

import pytest

from galaxy.app_unittest_utils import tools_support
from galaxy.app_unittest_utils.galaxy_mock import MockTrans
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.model import History
from galaxy.tools import ToolBox
from galaxy.workflow.modules import ToolModule
from .workflow_support import MockToolbox

CONDITIONAL = """<conditional name="conditional_parameter">
    <param name="test_parameter" type="boolean" />
    <when value="true">
        <param name="integer_parameter" type="integer" value="1" />
    </when>
    <when value="false">
        <param name="boolean_parameter" type="boolean" />
    </when>
</conditional>"""


class TestConditionalState(tools_support.UsesTools):
    def setup_method(self):
        self.setup_app()
        self.app._toolbox = cast(ToolBox, MockToolbox())
        self.trans = cast(ProvidesHistoryContext, MockTrans(self.app, history=History()))

    def teardown_method(self):
        self.tear_down_app()

    def _init_inputs(self, inputs=CONDITIONAL):
        self._init_tool(f"""<tool id="conditional_state" name="conditional_state" version="1.0">
            <command>echo</command>
            <inputs>{inputs}</inputs>
            <outputs><data name="out" format="txt" /></outputs>
        </tool>""")

    def _module(self, state, **kwds):
        with mock.patch.object(self.app.toolbox, "get_tool", return_value=self.tool):
            module = ToolModule(self.trans, self.tool.id)
        module.recover_state(deepcopy(state), **kwds)
        return module

    @pytest.mark.parametrize("checked", [False, True])
    @pytest.mark.parametrize("nested", [False, True])
    def test_missing_boolean_selector_warns_after_round_trip(self, checked, nested):
        inputs = CONDITIONAL.replace('type="boolean" />', f'type="boolean" checked="{checked}" />', 1)
        self._init_inputs(inputs)
        state = {"conditional_parameter": {"integer_parameter": 5}}
        imported = self._module(state)
        saved = json.loads(json.dumps(imported.get_state(nested=nested)))
        stored_conditional = saved["conditional_parameter"]
        if not nested:
            stored_conditional = json.loads(stored_conditional)
        assert stored_conditional == state["conditional_parameter"]
        loaded = self._module(saved)

        messages = loaded.check_and_update_state()

        message = messages["conditional_parameter|test_parameter"]
        assert "conditional_parameter|integer_parameter" in message
        assert "missing" in message.lower()
        assert "conditional_parameter|test_parameter" not in loaded.filled_defaults
        assert state == {"conditional_parameter": {"integer_parameter": 5}}
        # Loading the stored definition again must still require review.
        assert self._module(saved).check_and_update_state() == messages
        # Saving the reviewed correction must clear the warning.
        assert not self._module(loaded.get_state()).check_and_update_state()

    @pytest.mark.parametrize(
        "state",
        [
            {},
            {"conditional_parameter": {}},
            {"conditional_parameter": {"boolean_parameter": True}},
            {"conditional_parameter": {"test_parameter": True, "integer_parameter": 5}},
            {"conditional_parameter": {"test_parameter": False, "boolean_parameter": True}},
            {"conditional_parameter": {"test_parameter": None, "boolean_parameter": True}},
        ],
    )
    def test_valid_conditional_state_does_not_gain_warnings(self, state):
        self._init_inputs()
        imported = self._module(state)
        loaded = self._module(imported.get_state())

        assert not loaded.check_and_update_state()

    @pytest.mark.parametrize(
        "inputs,state,prefix",
        [
            (
                f'<section name="section" title="Section">{CONDITIONAL}</section>',
                {"section": {"conditional_parameter": {"integer_parameter": 5}}},
                "section|conditional_parameter|",
            ),
            (
                f'<repeat name="repeat" title="Repeat">{CONDITIONAL}</repeat>',
                {"repeat": [{"conditional_parameter": {"integer_parameter": 5}}]},
                "repeat_0|conditional_parameter|",
            ),
            (
                (
                    '<conditional name="outer"><param name="enabled" type="boolean" />'
                    f'<when value="true">{CONDITIONAL}</when><when value="false" /></conditional>'
                ),
                {"outer": {"enabled": True, "conditional_parameter": {"integer_parameter": 5}}},
                "outer|conditional_parameter|",
            ),
        ],
    )
    def test_nested_missing_selector_reports_full_input_path(self, inputs, state, prefix):
        self._init_inputs(inputs)
        loaded = self._module(self._module(state).get_state())

        message = loaded.check_and_update_state()[f"{prefix}test_parameter"]

        assert f"{prefix}integer_parameter" in message

    def test_filling_defaults_does_not_hide_lost_values(self):
        self._init_inputs()
        imported = self._module({"conditional_parameter": {"integer_parameter": 5}}, fill_defaults=True)
        loaded = self._module(imported.get_state())

        assert "conditional_parameter|test_parameter" in loaded.check_and_update_state()

    def test_missing_select_selector_reports_lost_values(self):
        inputs = CONDITIONAL.replace(
            '<param name="test_parameter" type="boolean" />',
            '<param name="test_parameter" type="select">'
            '<option value="true">True</option><option value="false">False</option></param>',
        )
        self._init_inputs(inputs)
        imported = self._module({"conditional_parameter": {"integer_parameter": 5}})
        loaded = self._module(imported.get_state())

        message = loaded.check_and_update_state()["conditional_parameter|test_parameter"]

        assert "conditional_parameter|integer_parameter" in message

    def test_explicit_form_correction_clears_warning(self):
        self._init_inputs()
        module = self._module({"conditional_parameter": {"integer_parameter": 5}})
        module.recover_state(
            {"conditional_parameter": {"test_parameter": True, "integer_parameter": 5}}, from_tool_form=True
        )
        loaded = self._module(module.get_state())

        assert not loaded.check_and_update_state()
        assert loaded.state.inputs["conditional_parameter"]["integer_parameter"] == 5
