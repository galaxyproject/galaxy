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

    @skip_without_tool("column_param_list")
    def test_build_module_multiple_data_column_input(self):
        module = self.workflow_populator.build_module(
            step_type="tool",
            content_id="column_param_list",
            inputs={"col": {"__class__": "ConnectedValue"}},
        )
        inputs = {step_input["name"]: step_input for step_input in module["inputs"]}
        assert inputs["col"]["type"] == "data_column"
        assert inputs["col"]["multiple"] is True

    @skip_without_tool("column_param")
    def test_build_module_single_data_column_input(self):
        module = self.workflow_populator.build_module(
            step_type="tool",
            content_id="column_param",
            inputs={"col": {"__class__": "ConnectedValue"}},
        )
        inputs = {step_input["name"]: step_input for step_input in module["inputs"]}
        assert inputs["col"]["type"] == "data_column"
        assert inputs["col"]["multiple"] is False

    @skip_without_tool("multi_select")
    def test_build_module_multiple_select_input(self):
        module = self.workflow_populator.build_module(
            step_type="tool",
            content_id="multi_select",
            inputs={"select_ex": {"__class__": "ConnectedValue"}},
        )
        inputs = {step_input["name"]: step_input for step_input in module["inputs"]}
        assert inputs["select_ex"]["type"] == "select"
        assert inputs["select_ex"]["multiple"] is True

    def test_build_module_multiple_integer_parameter(self):
        module = self.workflow_populator.build_module(
            step_type="parameter_input",
            inputs={
                "parameter_definition|parameter_type": "integer",
                "parameter_definition|multiple": True,
            },
        )
        assert not module["errors"], module["errors"]
        assert module["outputs"][0]["type"] == "integer"
        assert module["outputs"][0]["multiple"] is True
