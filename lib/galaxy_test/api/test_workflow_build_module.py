from galaxy_test.base.populators import (
    skip_without_tool,
    WorkflowPopulator,
)
from ._framework import ApiTestCase


class TestBuildWorkflowModule(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    @skip_without_tool("select_from_url")
    def test_build_module_filter_dynamic_select(self):
        # Verify that filtering on parameters that depend on parameter and validators works
        # fine in workflow building mode.
        module = self.workflow_populator.build_module(step_type="tool", content_id="select_from_url")
        assert not module["errors"], module["errors"]

    @skip_without_tool("format_source_in_conditional")
    def test_build_module_with_unresolvable_conditional_case(self):
        # A conditional value the tool no longer offers (e.g. after switching to an
        # older tool version) leaves the conditional on its default case, whose data
        # parameters must still be serializable as runtime values.
        module = self.workflow_populator.build_module(
            step_type="tool",
            content_id="format_source_in_conditional",
            inputs={"cond|select": "removed_option"},
        )
        assert module["errors"]["cond|select"]
        assert module["tool_state"]["cond"]["select"] == "removed_option"
        assert module["tool_state"]["cond"]["input1"] == {"__class__": "RuntimeValue"}

    def test_build_module_flags_inverted_numeric_bounds(self):
        inputs = {
            "parameter_definition|parameter_type": "integer",
            "parameter_definition|optional|optional": "false",
            "parameter_definition|min": "5",
            "parameter_definition|max": "1",
        }
        module = self.workflow_populator.build_module(step_type="parameter_input", inputs=inputs)
        assert module["errors"] == "A workflow input has a minimum (5) greater than its maximum (1)."
        inputs["parameter_definition|max"] = "10"
        module = self.workflow_populator.build_module(step_type="parameter_input", inputs=inputs)
        assert module["errors"] is None
