import contextlib
import json

from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.workflows import RefactorRequest
from galaxy.model import (
    PostJobAction,
    PostJobActionAssociation,
    StoredWorkflow,
    User,
    Workflow,
    WorkflowOutput,
    WorkflowStep,
    WorkflowStepConnection,
)
from galaxy.workflow.refactor.schema import RefactorActionExecutionMessageTypeEnum
from galaxy_test.base.populators import WorkflowPopulator
from galaxy_test.base.uses_shed import UsesShed
from galaxy_test.base.workflow_fixtures import (
    WORKFLOW_NESTED_RUNTIME_PARAMETER,
    WORKFLOW_NESTED_SIMPLE,
    WORKFLOW_NESTED_WITH_MULTIPLE_VERSIONS_TOOL,
)
from galaxy_test.driver import integration_util

REFACTORING_SIMPLE_TEST = """
class: GalaxyWorkflow
inputs:
  test_input: data
outputs:
  wf_out:
    outputSource: first_cat/out_file1
steps:
  first_cat:
    tool_id: cat
    in:
      input1: test_input
"""


class WorkflowRefactoringIntegrationTestCase(integration_util.IntegrationTestCase, UsesShed):

    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_basic_refactoring_types(self):
        self.workflow_populator.upload_yaml_workflow(REFACTORING_SIMPLE_TEST)

        actions = [
            {"action_type": "update_name", "name": "my cool new name"},
        ]
        self._refactor(actions)
        assert self._latest_workflow.stored_workflow.name == "my cool new name"

        actions = [
            {"action_type": "update_annotation", "annotation": "my cool new annotation"},
        ]
        response = self._refactor(actions)
        assert response.workflow["annotation"] == "my cool new annotation"

        actions = [
            {"action_type": "update_license", "license": "AFL-3.0"},
        ]
        self._refactor(actions)
        assert self._latest_workflow.license == "AFL-3.0"

        actions = [
            {"action_type": "update_creator", "creator": [{"class": "Person", "name": "Mary"}]},
        ]
        self._refactor(actions)
        assert self._latest_workflow.creator_metadata[0]["class"] == "Person"
        assert self._latest_workflow.creator_metadata[0]["name"] == "Mary"

        actions = [{"action_type": "update_report", "report": {"markdown": "my report..."}}]
        self._refactor(actions)
        assert self._latest_workflow.reports_config["markdown"] == "my report..."

        assert self._latest_workflow.step_by_index(0).label == "test_input"
        actions = [
            {"action_type": "update_step_label", "step": {"order_index": 0}, "label": "new_label"},
        ]
        self._refactor(actions)
        assert self._latest_workflow.step_by_index(0).label == "new_label"

        # Build raw steps...
        actions = [
            {
                "action_type": "add_step",
                "type": "parameter_input",
                "label": "new_param",
                "tool_state": {"parameter_type": "text"},
                "position": {"left": 10, "top": 50},
            },
        ]
        self._refactor(actions)
        assert self._latest_workflow.step_by_label("new_param").label == "new_param"
        assert self._latest_workflow.step_by_label("new_param").tool_inputs.get("optional", False) is False
        assert self._latest_workflow.step_by_label("new_param").position["left"] == 10
        assert self._latest_workflow.step_by_label("new_param").position["top"] == 50

        # update new_param positions
        actions = [
            {
                "action_type": "update_step_position",
                "step": {"label": "new_param"},
                "position_shift": {"left": 3, "top": 5},
            },
        ]
        self._refactor(actions)
        assert self._latest_workflow.step_by_index(1).label == "new_param"
        assert self._latest_workflow.step_by_index(1).position["left"] == 13
        assert self._latest_workflow.step_by_index(1).position["top"] == 55

        # Cleaner syntax for defining inputs...
        actions = [
            {
                "action_type": "add_input",
                "type": "text",
                "label": "new_param2",
                "optional": True,
                "position": {"top": 1, "left": 2},
            },
        ]
        self._refactor(actions)
        assert self._latest_workflow.step_by_label("new_param2").label == "new_param2"
        assert self._latest_workflow.step_by_label("new_param2").tool_inputs.get("optional", False) is True
        assert self._latest_workflow.step_by_label("new_param2").position["top"] == 1
        assert self._latest_workflow.step_by_label("new_param2").position["left"] == 2

        assert len(self._latest_workflow.step_by_label("first_cat").inputs) == 1
        actions = [
            {
                "action_type": "disconnect",
                "input": {"label": "first_cat", "input_name": "input1"},
                "output": {"label": "new_label"},
            }
        ]
        self._refactor(actions)
        assert len(self._latest_workflow.step_by_label("first_cat").inputs) == 0

        actions = [
            {
                "action_type": "connect",
                "input": {"label": "first_cat", "input_name": "input1"},
                "output": {"label": "new_label"},
            }
        ]
        self._refactor(actions)
        assert len(self._latest_workflow.step_by_label("first_cat").inputs) == 1

        # Re-disconnect so we can test extract_input
        actions = [
            {
                "action_type": "disconnect",
                "input": {"label": "first_cat", "input_name": "input1"},
                "output": {"label": "new_label"},
            }
        ]
        self._refactor(actions)

        # try to create an input for first_cat/input1 automatically
        actions = [
            {
                "action_type": "extract_input",
                "input": {"label": "first_cat", "input_name": "input1"},
                "label": "extracted_input",
            }
        ]
        self._refactor(actions)
        assert self._latest_workflow.step_by_label("extracted_input")
        assert len(self._latest_workflow.step_by_label("first_cat").inputs) == 1

        actions = [
            {
                "action_type": "update_output_label",
                "output": {"label": "first_cat", "output_name": "out_file1"},
                "output_label": "new_wf_out",
            }
        ]
        self._refactor(actions)
        assert self._latest_workflow.step_by_label("first_cat").workflow_outputs[0].label == "new_wf_out"

    def test_basic_refactoring_types_dry_run(self):
        self.workflow_populator.upload_yaml_workflow(REFACTORING_SIMPLE_TEST)

        actions = [
            {"action_type": "update_name", "name": "my cool new name"},
        ]
        response = self._dry_run(actions)
        assert response.workflow["name"] == "my cool new name"

        actions = [
            {"action_type": "update_annotation", "annotation": "my cool new annotation"},
        ]
        response = self._dry_run(actions)
        assert response.workflow["annotation"] == "my cool new annotation"

        actions = [
            {"action_type": "update_license", "license": "AFL-3.0"},
        ]
        response = self._dry_run(actions)
        assert response.workflow["license"] == "AFL-3.0"

        actions = [
            {"action_type": "update_creator", "creator": [{"class": "Person", "name": "Mary"}]},
        ]
        response = self._dry_run(actions)
        creator_list = response.workflow["creator"]
        assert isinstance(creator_list, list)
        creator = creator_list[0]
        assert creator["class"] == "Person"
        assert creator["name"] == "Mary"

        actions = [{"action_type": "update_report", "report": {"markdown": "my report..."}}]
        response = self._dry_run(actions)
        assert response.workflow["report"]["markdown"] == "my report..."

        actions = [
            {
                "action_type": "add_step",
                "type": "parameter_input",
                "label": "new_param",
                "tool_state": {"parameter_type": "text"},
                "position": {"left": 10, "top": 50},
            },
        ]
        response = self._dry_run(actions)
        workflow_dict = response.workflow
        assert _step_with_label(workflow_dict, "new_param")

        actions = [
            {
                "action_type": "update_output_label",
                "output": {"label": "first_cat", "output_name": "out_file1"},
                "output_label": "new_wf_out",
            }
        ]
        response = self._dry_run(actions)
        workflow_dict = response.workflow
        first_cat_step = _step_with_label(workflow_dict, "first_cat")
        assert first_cat_step["workflow_outputs"][0]["label"] == "new_wf_out"

    def test_refactoring_legacy_parameters(self):
        wf = self.workflow_populator.load_workflow_from_resource("test_workflow_randomlines_legacy_params")
        self.workflow_populator.create_workflow(wf)
        actions = [
            {"action_type": "extract_untyped_parameter", "name": "seed"},
            {"action_type": "extract_untyped_parameter", "name": "num", "label": "renamed_num"},
        ]
        self._refactor(actions)
        assert self._latest_workflow.step_by_label("seed").tool_inputs["parameter_type"] == "text"
        assert self._latest_workflow.step_by_label("renamed_num").tool_inputs["parameter_type"] == "integer"
        random_lines_state = self._latest_workflow.step_by_index(2).tool_inputs
        assert "num_lines" in random_lines_state
        num_lines = random_lines_state["num_lines"]
        assert isinstance(num_lines, dict)
        assert "__class__" in num_lines
        assert num_lines["__class__"] == "ConnectedValue"
        assert "seed_source" in random_lines_state
        seed_source = random_lines_state["seed_source"]
        assert isinstance(seed_source, dict)
        assert "seed" in seed_source
        seed = seed_source["seed"]
        assert isinstance(seed, dict)
        assert "__class__" in seed
        assert seed["__class__"] == "ConnectedValue"

        # cannot handle mixed, incompatible types on the inputs though
        wf = self.workflow_populator.load_workflow_from_resource("test_workflow_randomlines_legacy_params_mixed_types")
        self.workflow_populator.create_workflow(wf)
        actions = [
            {"action_type": "extract_untyped_parameter", "name": "mixed_param"},
        ]
        expected_exception = None
        try:
            self._refactor(actions)
        except Exception as e:
            expected_exception = e
        assert expected_exception
        assert "input types" in str(expected_exception)

    def test_refactoring_legacy_parameters_without_tool_state(self):
        # test parameters used in PJA without being used in tool state.
        # These will work fine with the simplified workflow UI, but should probably
        # be formalized and assigned a unique label and informative annotation.
        self.workflow_populator.upload_yaml_workflow(
            """
class: GalaxyWorkflow
inputs:
  test_input: data
steps:
  first_cat:
    tool_id: cat
    in:
      input1: test_input
    outputs:
      out_file1:
        rename: "${pja_only_param} name"
"""
        )
        actions = [
            {"action_type": "extract_untyped_parameter", "name": "pja_only_param"},
        ]
        self._refactor(actions)
        assert self._latest_workflow.step_by_label("pja_only_param").tool_inputs["parameter_type"] == "text"

    def test_refactoring_legacy_parameters_without_tool_state_dry_run(self):
        # same as above but dry run...
        self.workflow_populator.upload_yaml_workflow(
            """
class: GalaxyWorkflow
inputs:
  test_input: data
steps:
  first_cat:
    tool_id: cat
    in:
      input1: test_input
    outputs:
      out_file1:
        rename: "${pja_only_param} name"
"""
        )
        actions = [
            {"action_type": "extract_untyped_parameter", "name": "pja_only_param"},
        ]
        response = self._dry_run(actions)
        new_step = _step_with_label(response.workflow, "pja_only_param")
        state_str = new_step["tool_state"]
        state = json.loads(state_str)
        assert state["parameter_type"] == "text"

    def test_refactoring_legacy_parameters_without_tool_state_relabel(self):
        # same thing as above, but apply relabeling and ensure PJA gets updated.
        self.workflow_populator.upload_yaml_workflow(
            """
class: GalaxyWorkflow
inputs:
  test_input: data
steps:
  first_cat:
    tool_id: cat
    in:
      input1: test_input
    outputs:
      out_file1:
        rename: "${pja_only_param} name"
"""
        )
        actions = [
            {"action_type": "extract_untyped_parameter", "name": "pja_only_param", "label": "new_label"},
        ]
        self._refactor(actions)
        assert self._latest_workflow.step_by_label("new_label").tool_inputs["parameter_type"] == "text"
        pjas = self._latest_workflow.step_by_label("first_cat").post_job_actions
        assert len(pjas) == 1
        pja = pjas[0]
        assert "newname" in pja.action_arguments
        assert "${new_label}" in pja.action_arguments["newname"]

    def test_removing_unlabeled_workflow_outputs(self):
        wf = self.workflow_populator.load_workflow_from_resource("test_workflow_randomlines_legacy_params")
        self.workflow_populator.create_workflow(wf)
        only_step = self._latest_workflow.step_by_index(0)
        assert len(only_step.workflow_outputs) == 1
        actions = [
            {"action_type": "remove_unlabeled_workflow_outputs"},
        ]
        self._refactor(actions)
        only_step = self._latest_workflow.step_by_index(0)
        assert len(only_step.workflow_outputs) == 0

    def test_fill_defaults_option(self):
        # this is a prereq for other state filling refactoring tests that
        # would be better in API tests for workflow import options but fill
        # defaults happens automatically on export, so this might only be
        # testable in an integration test currently.

        # populating a workflow with incomplete state...
        wf = self.workflow_populator.load_workflow_from_resource("test_workflow_two_random_lines")
        ts = json.loads(wf["steps"]["0"]["tool_state"])
        del ts["num_lines"]
        wf["steps"]["0"]["tool_state"] = json.dumps(ts)
        self.workflow_populator.create_workflow(wf, fill_defaults=False)
        first_step = self._latest_workflow.step_by_label("random1")
        assert "num_lines" not in first_step.tool_inputs

        self.workflow_populator.create_workflow(wf, fill_defaults=True)
        first_step = self._latest_workflow.step_by_label("random1")
        assert "num_lines" in first_step.tool_inputs
        assert json.loads(first_step.tool_inputs["num_lines"]) == 1

    def test_refactor_works_with_subworkflows(self):
        self.workflow_populator.upload_yaml_workflow(WORKFLOW_NESTED_SIMPLE)
        actions = [
            {"action_type": "update_step_label", "step": {"label": "nested_workflow"}, "label": "new_nested_workflow"},
        ]
        self._refactor(actions)
        self._latest_workflow.step_by_label("new_nested_workflow")

    def test_refactor_works_with_incomplete_state(self):
        # populating a workflow with incomplete state...
        wf = self.workflow_populator.load_workflow_from_resource("test_workflow_two_random_lines")
        ts = json.loads(wf["steps"]["0"]["tool_state"])
        del ts["num_lines"]
        wf["steps"]["0"]["tool_state"] = json.dumps(ts)
        self.workflow_populator.create_workflow(wf, fill_defaults=False)

        assert self._latest_workflow.step_by_index(0).label == "random1"
        actions = [
            {"action_type": "update_step_label", "step": {"order_index": 0}, "label": "random1_new"},
        ]
        self._refactor(actions)
        first_step = self._latest_workflow.step_by_label("random1_new")
        assert "num_lines" not in first_step.tool_inputs

    def test_refactor_works_with_missing_tools(self):
        # populating a workflow with incomplete state...
        wf = self.workflow_populator.load_workflow_from_resource("test_workflow_two_random_lines")
        wf["steps"]["1"]["tool_id"] = "random-missing"
        wf["steps"]["1"]["content_id"] = "random-missing"
        self.workflow_populator.create_workflow(wf, fill_defaults=False)

        assert self._latest_workflow.step_by_index(1).label == "random2"
        assert self._latest_workflow.step_by_index(1).tool_id == "random-missing"
        assert "num_lines" in self._latest_workflow.step_by_index(1).tool_inputs

        actions = [
            {"action_type": "update_step_label", "step": {"order_index": 1}, "label": "random2_new"},
        ]
        self._refactor(actions)
        assert self._latest_workflow.step_by_index(1).label == "random2_new"
        assert "num_lines" in self._latest_workflow.step_by_index(1).tool_inputs

    def test_refactor_fill_step_defaults(self):
        self._load_two_random_lines_wf_with_missing_state()
        actions = [
            {"action_type": "fill_step_defaults", "step": {"order_index": 0}},
        ]
        action_executions = self._refactor(actions).action_executions
        first_step = self._latest_workflow.step_by_label("random1")
        assert "num_lines" in first_step.tool_inputs
        assert len(action_executions) == 1
        action_execution = action_executions[0]
        assert len(action_execution.messages) == 1
        message = action_execution.messages[0]
        assert message.order_index == 0
        assert message.step_label == "random1"
        assert message.input_name == "num_lines"

        # ensure other step untouched...
        second_step = self._latest_workflow.step_by_label("random2")
        assert "num_lines" not in second_step.tool_inputs

    def test_refactor_fill_step_defaults_dry_run(self):
        self._load_two_random_lines_wf_with_missing_state()
        actions = [
            {"action_type": "fill_step_defaults", "step": {"order_index": 0}},
        ]
        response = self._dry_run(actions)
        action_executions = response.action_executions
        assert len(action_executions) == 1
        action_execution = action_executions[0]
        assert len(action_execution.messages) == 1
        message = action_execution.messages[0]
        assert message.order_index == 0
        assert message.step_label == "random1"
        assert message.input_name == "num_lines"

        # TODO:
        # first_step = self._latest_workflow.step_by_label("random1")
        # assert "num_lines" in first_step.tool_inputs

        # ensure other step untouched...
        # second_step = self._latest_workflow.step_by_label("random2")
        # assert "num_lines" not in second_step.tool_inputs

    def test_refactor_fill_defaults(self):
        self._load_two_random_lines_wf_with_missing_state()
        actions = [
            {"action_type": "fill_defaults"},
        ]
        action_executions = self._refactor(actions).action_executions

        first_step = self._latest_workflow.step_by_label("random1")
        assert "num_lines" in first_step.tool_inputs
        second_step = self._latest_workflow.step_by_label("random2")
        assert "num_lines" in second_step.tool_inputs

        assert len(action_executions) == 1
        action_execution = action_executions[0]
        assert len(action_execution.messages) == 2
        message = action_execution.messages[0]
        assert message.order_index == 0
        assert message.step_label == "random1"
        assert message.input_name == "num_lines"
        message = action_execution.messages[1]
        assert message.order_index == 1
        assert message.step_label == "random2"
        assert message.input_name == "num_lines"

    def test_tool_version_upgrade_no_state_change(self):
        self.workflow_populator.upload_yaml_workflow(
            """
class: GalaxyWorkflow
steps:
  the_step:
    tool_id: multiple_versions
    tool_version: '0.1'
    state:
      inttest: 0
"""
        )
        assert self._latest_workflow.step_by_label("the_step").tool_version == "0.1"
        actions = [
            {"action_type": "upgrade_tool", "step": {"label": "the_step"}},
        ]
        # t = self._app.toolbox.get_tool("multiple_versions", tool_version="0.1")
        # assert t is not None
        # assert t.version == "0.1"
        action_executions = self._refactor(actions).action_executions
        assert len(action_executions) == 1
        assert len(action_executions[0].messages) == 0
        assert self._latest_workflow.step_by_label("the_step").tool_version == "0.2"

    def test_tool_version_upgrade_state_added(self):
        self.workflow_populator.upload_yaml_workflow(
            """
class: GalaxyWorkflow
steps:
  the_step:
    tool_id: multiple_versions_changes
    tool_version: '0.1'
    state:
      inttest: 0
"""
        )
        assert self._latest_workflow.step_by_label("the_step").tool_version == "0.1"
        actions = [
            {"action_type": "upgrade_tool", "step": {"label": "the_step"}, "tool_version": "0.2"},
        ]
        action_executions = self._refactor(actions).action_executions

        assert self._latest_workflow.step_by_label("the_step").tool_version == "0.2"

        assert len(action_executions) == 1
        messages = action_executions[0].messages
        assert len(messages) == 1
        message = messages[0]
        assert message.message_type == RefactorActionExecutionMessageTypeEnum.tool_state_adjustment
        assert message.order_index == 0
        assert message.step_label == "the_step"
        assert message.input_name == "floattest"

    def test_subworkflow_upgrade_simplest(self):
        self.workflow_populator.upload_yaml_workflow(WORKFLOW_NESTED_SIMPLE)
        # second oldest workflow will be the nested workflow, grab it and update...
        nested_stored_workflow = self._recent_stored_workflow(2)
        assert len(nested_stored_workflow.workflows) == 1

        self._increment_nested_workflow_version(nested_stored_workflow, num_lines_from="1", num_lines_to="2")
        self._app.model.session.expunge(nested_stored_workflow)
        # ensure subworkflow updated properly...
        nested_stored_workflow = self._recent_stored_workflow(2)
        assert len(nested_stored_workflow.workflows) == 2
        updated_nested_step = nested_stored_workflow.latest_workflow.step_by_label("random_lines")
        assert updated_nested_step.tool_inputs["num_lines"] == "2"

        # we now have an nested workflow with a simple update, download
        # the target workflow and ensure it is pointing at the old version
        pre_upgrade_native = self._download_native(self._most_recent_stored_workflow)
        self._assert_nested_workflow_num_lines_is(pre_upgrade_native, "1")

        actions = [
            {"action_type": "upgrade_subworkflow", "step": {"label": "nested_workflow"}},
        ]
        response = self._dry_run(actions)
        action_executions = response.action_executions
        assert len(action_executions) == 1
        assert len(action_executions[0].messages) == 0

        action_executions = self._refactor(actions).action_executions
        assert len(action_executions) == 1
        assert len(action_executions[0].messages) == 0

        post_upgrade_native = self._download_native(self._most_recent_stored_workflow)
        self._assert_nested_workflow_num_lines_is(post_upgrade_native, "2")

    def test_subworkflow_upgrade_specified(self):
        self.workflow_populator.upload_yaml_workflow(WORKFLOW_NESTED_SIMPLE)
        # second oldest workflow will be the nested workflow, grab it and update...
        nested_stored_workflow = self._recent_stored_workflow(2)

        # create two versions so we can test jumping to the middle one...
        self._increment_nested_workflow_version(nested_stored_workflow, num_lines_from="1", num_lines_to="20")
        self._increment_nested_workflow_version(nested_stored_workflow, num_lines_from="20", num_lines_to="30")
        self._app.model.session.expunge(nested_stored_workflow)
        # ensure subworkflow updated properly...
        nested_stored_workflow = self._recent_stored_workflow(2)
        assert len(nested_stored_workflow.workflows) == 3
        middle_workflow_id = self._app.security.encode_id(nested_stored_workflow.workflows[1].id)
        actions = [
            {
                "action_type": "upgrade_subworkflow",
                "step": {"label": "nested_workflow"},
                "content_id": middle_workflow_id,
            },
        ]
        action_executions = self._dry_run(actions).action_executions
        assert len(action_executions) == 1
        assert len(action_executions[0].messages) == 0

        action_executions = self._refactor(actions).action_executions
        assert len(action_executions) == 1
        assert len(action_executions[0].messages) == 0
        post_upgrade_native = self._download_native(self._most_recent_stored_workflow)
        self._assert_nested_workflow_num_lines_is(post_upgrade_native, "20")

    def test_subworkflow_upgrade_connection_input_dropped(self):
        self.workflow_populator.upload_yaml_workflow(WORKFLOW_NESTED_SIMPLE)

        nested_stored_workflow = self._recent_stored_workflow(2)
        actions = [
            {"action_type": "update_step_label", "step": {"label": "inner_input"}, "label": "renamed_inner_input"},
        ]
        self._refactor(actions, stored_workflow=nested_stored_workflow)

        actions = [
            {"action_type": "upgrade_subworkflow", "step": {"label": "nested_workflow"}},
        ]
        action_executions = self._refactor(actions).action_executions
        native_dict = self._download_native()
        nested_step = _step_with_label(native_dict, "nested_workflow")
        # order_index of subworkflow shifts down from "2" because it has no
        # inbound inputs
        assert nested_step["subworkflow"]["steps"]["0"]["label"] == "renamed_inner_input"
        assert len(action_executions) == 1
        messages = action_executions[0].messages
        assert len(messages) == 1

        message = messages[0]
        assert message.message_type == RefactorActionExecutionMessageTypeEnum.connection_drop_forced
        assert message.order_index == 2
        assert message.step_label == "nested_workflow"
        assert message.input_name == "inner_input"
        assert message.from_step_label == "first_cat"
        assert message.from_order_index == 1
        assert message.output_name == "out_file1"

    def test_subworkflow_upgrade_connection_output_dropped(self):
        self.workflow_populator.upload_yaml_workflow(WORKFLOW_NESTED_SIMPLE)

        nested_stored_workflow = self._recent_stored_workflow(2)
        actions = [
            {
                "action_type": "update_output_label",
                "output": {"label": "random_lines", "output_name": "out_file1"},
                "output_label": "renamed_output",
            }
        ]
        self._refactor(actions, stored_workflow=nested_stored_workflow)

        actions = [
            {"action_type": "upgrade_subworkflow", "step": {"label": "nested_workflow"}},
        ]
        action_executions = self._refactor(actions).action_executions
        assert len(action_executions) == 1
        messages = action_executions[0].messages

        # it was connected to two inputs on second_cat step
        assert len(messages) == 2
        for message in messages:
            assert message.message_type == RefactorActionExecutionMessageTypeEnum.connection_drop_forced
            assert message.order_index == 3
            assert message.step_label == "second_cat"
            assert message.input_name in ["input1", "queries_0|input2"]
            assert message.from_step_label == "nested_workflow"
            assert message.from_order_index == 2
            assert message.output_name == "workflow_output"

    def test_subworkflow_upgrade_output_label_dropped(self):
        self.workflow_populator.upload_yaml_workflow(WORKFLOW_NESTED_RUNTIME_PARAMETER)

        nested_stored_workflow = self._recent_stored_workflow(2)
        actions = [
            {
                "action_type": "update_output_label",
                "output": {"label": "random_lines", "output_name": "out_file1"},
                "output_label": "renamed_output",
            }
        ]
        self._refactor(actions, stored_workflow=nested_stored_workflow)

        actions = [
            {"action_type": "upgrade_subworkflow", "step": {"label": "nested_workflow"}},
        ]
        action_executions = self._refactor(actions).action_executions
        assert len(action_executions) == 1
        messages = action_executions[0].messages
        assert len(messages) == 1

        message = messages[0]
        assert message.message_type == RefactorActionExecutionMessageTypeEnum.workflow_output_drop_forced
        assert message.order_index == 1
        assert message.step_label == "nested_workflow"
        assert message.output_name == "workflow_output"
        assert message.output_label == "outer_output"

    def test_upgrade_all_steps(self):
        self.install_repository("iuc", "compose_text_param", "feb3acba1e0a")  # 0.1.0
        self.install_repository("iuc", "compose_text_param", "e188c9826e0f")  # 0.1.1
        self.workflow_populator.upload_yaml_workflow(WORKFLOW_NESTED_WITH_MULTIPLE_VERSIONS_TOOL)
        nested_stored_workflow = self._recent_stored_workflow(2)
        assert self._latest_workflow.step_by_label("tool_update_step").tool_version == "0.1"
        updated_nested_step = nested_stored_workflow.latest_workflow.step_by_label("random_lines")
        assert updated_nested_step.tool_inputs["num_lines"] == "1"

        self._increment_nested_workflow_version(nested_stored_workflow, num_lines_from="1", num_lines_to="2")
        self._app.model.session.expunge(nested_stored_workflow)
        # ensure subworkflow updated properly...
        nested_stored_workflow = self._recent_stored_workflow(2)
        assert len(nested_stored_workflow.workflows) == 2
        actions = [
            {"action_type": "upgrade_all_steps"},
        ]
        action_executions = self._refactor(actions).action_executions
        assert self._latest_workflow.step_by_label("tool_update_step").tool_version == "0.2"
        nested_stored_workflow = self._recent_stored_workflow(2)
        updated_nested_step = nested_stored_workflow.latest_workflow.step_by_label("random_lines")
        assert updated_nested_step.tool_inputs["num_lines"] == "2"
        assert self._latest_workflow.step_by_label("compose_text_param").tool_version == "0.1.1"
        assert (
            self._latest_workflow.step_by_label("compose_text_param").tool_id
            == "toolshed.g2.bx.psu.edu/repos/iuc/compose_text_param/compose_text_param/0.1.1"
        )

        assert len(action_executions) == 1
        messages = action_executions[0].messages
        assert len(messages) == 1
        message = messages[0]
        assert message.message_type == RefactorActionExecutionMessageTypeEnum.connection_drop_forced
        assert message.order_index == 2
        assert message.step_label == "tool_update_step"
        assert message.output_name == "output"

    def _download_native(self, workflow=None):
        workflow = workflow or self._most_recent_stored_workflow
        workflow_id = self._app.security.encode_id(workflow.id)
        return self.workflow_populator.download_workflow(workflow_id)

    @contextlib.contextmanager
    def _export_for_update(self, workflow):
        workflow_id = self._app.security.encode_id(workflow.id)
        with self.workflow_populator.export_for_update(workflow_id) as workflow_object:
            yield workflow_object

    def _refactor(self, actions, stored_workflow=None, dry_run=False, style="ga"):
        user = self._app.model.session.query(User).order_by(User.id.desc()).limit(1).one()
        mock_trans = MockTrans(self._app, user)

        app = self._app
        original_url_for = app.url_for

        def url_for(*args, **kwd):
            return ""

        app.url_for = url_for
        try:
            return self._manager.refactor(
                mock_trans,
                stored_workflow or self._most_recent_stored_workflow,
                RefactorRequest(actions=actions, dry_run=dry_run, style=style),
            )
        finally:
            app = url_for = original_url_for

    def _dry_run(self, actions, stored_workflow=None):
        # Do a bunch of checks to ensure nothing workflow related was written to the database
        # or even added to the sa_session.
        sa_session = self._app.model.session
        sa_session.flush()

        sw_update_time = self._model_last_time(StoredWorkflow)
        assert sw_update_time
        w_update_time = self._model_last_time(Workflow)
        assert w_update_time
        ws_last_id = self._model_last_id(WorkflowStep)
        assert ws_last_id
        wsc_last_id = self._model_last_id(WorkflowStepConnection)
        pja_last_id = self._model_last_id(PostJobAction)
        pjaa_last_id = self._model_last_id(PostJobActionAssociation)
        wo_last_id = self._model_last_id(WorkflowOutput)

        response = self._refactor(actions, stored_workflow=stored_workflow, dry_run=True)
        sa_session.flush()
        sa_session.expunge_all()
        assert sw_update_time == self._model_last_time(StoredWorkflow)
        assert w_update_time == self._model_last_time(Workflow)
        assert ws_last_id == self._model_last_id(WorkflowStep)
        assert wsc_last_id == self._model_last_id(WorkflowStepConnection)
        assert pja_last_id == self._model_last_id(PostJobAction)
        assert pjaa_last_id == self._model_last_id(PostJobActionAssociation)
        assert wo_last_id == self._model_last_id(WorkflowOutput)

        return response

    def _model_last_time(self, clazz):
        obj = self._app.model.session.query(clazz).order_by(clazz.update_time.desc()).limit(1).one()
        return obj.update_time

    def _model_last_id(self, clazz):
        obj = self._app.model.session.query(clazz).order_by(clazz.id.desc()).limit(1).one_or_none()
        return obj.id if obj else None

    @property
    def _manager(self):
        return self._app.workflow_contents_manager

    @property
    def _most_recent_stored_workflow(self):
        return self._recent_stored_workflow(1)

    def _recent_stored_workflow(self, n=1):
        app = self._app
        return app.model.session.query(StoredWorkflow).order_by(StoredWorkflow.id.desc()).limit(n).all()[-1]

    @property
    def _latest_workflow(self):
        return self._most_recent_stored_workflow.latest_workflow

    def _increment_nested_workflow_version(self, nested_stored_workflow, num_lines_from="1", num_lines_to="2"):
        # increment nested workflow from WORKFLOW_NESTED_SIMPLE with
        # new num_lines in the tool state of the random_lines1 step.
        with self._export_for_update(nested_stored_workflow) as native_workflow_dict:
            tool_step = native_workflow_dict["steps"]["1"]
            assert tool_step["type"] == "tool"
            assert tool_step["tool_id"] == "random_lines1"
            tool_state_json = tool_step["tool_state"]
            tool_state = json.loads(tool_state_json)
            assert tool_state["num_lines"] == num_lines_from
            tool_state["num_lines"] = num_lines_to
            tool_step["tool_state"] = json.dumps(tool_state)

    def _assert_nested_workflow_num_lines_is(self, native_dict, num_lines):
        # assuming native_dict is the .ga representation of WORKFLOW_NESTED_SIMPLE,
        # or some update created with _increment_nested_workflow_version, assert
        # the nested num_lines step is as specified
        target_out_step = native_dict["steps"]["2"]
        assert "subworkflow" in target_out_step
        target_subworkflow = target_out_step["subworkflow"]
        target_state_json = target_subworkflow["steps"]["1"]["tool_state"]
        target_state = json.loads(target_state_json)
        assert target_state["num_lines"] == num_lines

    def _load_two_random_lines_wf_with_missing_state(self):
        wf = self.workflow_populator.load_workflow_from_resource("test_workflow_two_random_lines")
        ts = json.loads(wf["steps"]["0"]["tool_state"])
        del ts["num_lines"]
        wf["steps"]["0"]["tool_state"] = json.dumps(ts)
        wf["steps"]["1"]["tool_state"] = json.dumps(ts)
        self.workflow_populator.create_workflow(wf, fill_defaults=False)

        first_step = self._latest_workflow.step_by_label("random1")
        assert "num_lines" not in first_step.tool_inputs
        second_step = self._latest_workflow.step_by_label("random2")
        assert "num_lines" not in second_step.tool_inputs


def _step_with_label(native_dict, label):
    for step_dict in native_dict["steps"].values():
        if step_dict.get("label") == label:
            return step_dict
    raise AssertionError(f"Failed to find step with label {label}")


class MockTrans(ProvidesAppContext):
    def __init__(self, app, user):
        self._app = app
        self.user = user
        self.history = None

    @property
    def app(self):
        return self._app
