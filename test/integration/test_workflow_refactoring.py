import json

from galaxy.managers.context import ProvidesAppContext
from galaxy.workflow.refactor.schema import RefactorRequest
from galaxy_test.base.populators import (
    WorkflowPopulator,
)
from galaxy_test.driver import integration_util


class WorkflowRefactoringIntegrationTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_basic_refactoring_types(self):
        self.workflow_populator.upload_yaml_workflow("""
class: GalaxyWorkflow
inputs:
  test_input: data
steps:
  first_cat:
    tool_id: cat
    in:
      input1: test_input
""")

        actions = [
            {"action_type": "update_name", "name": "my cool new name"},
        ]
        self._refactor_without_errors(actions)
        assert self._latest_workflow.stored_workflow.name == "my cool new name"

        actions = [
            {"action_type": "update_annotation", "annotation": "my cool new annotation"},
        ]
        self._refactor_without_errors(actions)
        # TODO: test annotation change...

        actions = [
            {"action_type": "update_license", "license": "AFL-3.0"},
        ]
        self._refactor_without_errors(actions)
        assert self._latest_workflow.license == "AFL-3.0"

        actions = [
            {"action_type": "update_creator", "creator": [{"class": "Person", "name": "Mary"}]},
        ]
        self._refactor_without_errors(actions)
        assert self._latest_workflow.creator_metadata[0]["class"] == "Person"
        assert self._latest_workflow.creator_metadata[0]["name"] == "Mary"

        actions = [
            {"action_type": "update_report", "report": {"markdown": "my report..."}}
        ]
        self._refactor_without_errors(actions)
        assert self._latest_workflow.reports_config["markdown"] == "my report..."

        assert self._latest_workflow.step_by_index(0).label == "test_input"
        actions = [
            {"action_type": "update_step_label", "step": {"order_index": 0}, "label": "new_label"},
        ]
        self._refactor_without_errors(actions)
        assert self._latest_workflow.step_by_index(0).label == "new_label"

        actions = [
            {"action_type": "update_step_position", "step": {"order_index": 0}, "position": {"left": 3, "top": 5}},
        ]
        self._refactor_without_errors(actions)
        assert self._latest_workflow.step_by_index(0).label == "new_label"
        assert self._latest_workflow.step_by_index(0).position["left"] == 3
        assert self._latest_workflow.step_by_index(0).position["top"] == 5

        # Build raw steps...
        actions = [
            {"action_type": "add_step", "type": "parameter_input", "label": "new_param", "tool_state": {"parameter_type": "text"}, "position": {"left": 10, "top": 50}},
        ]
        self._refactor_without_errors(actions)
        assert self._latest_workflow.step_by_label("new_param").label == "new_param"
        assert self._latest_workflow.step_by_label("new_param").tool_inputs.get("optional", False) is False
        assert self._latest_workflow.step_by_label("new_param").position["left"] == 10
        assert self._latest_workflow.step_by_label("new_param").position["top"] == 50

        # Cleaner syntax for defining inputs...
        actions = [
            {"action_type": "add_input", "type": "text", "label": "new_param2", "optional": True, "position": {"top": 1, "left": 2}},
        ]
        self._refactor_without_errors(actions)
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
        self._refactor_without_errors(actions)
        assert len(self._latest_workflow.step_by_label("first_cat").inputs) == 0

        actions = [
            {
                "action_type": "connect",
                "input": {"label": "first_cat", "input_name": "input1"},
                "output": {"label": "new_label"},
            }
        ]
        self._refactor_without_errors(actions)
        assert len(self._latest_workflow.step_by_label("first_cat").inputs) == 1

        # Re-disconnect so we can test extract_input
        actions = [
            {
                "action_type": "disconnect",
                "input": {"label": "first_cat", "input_name": "input1"},
                "output": {"label": "new_label"},
            }
        ]
        self._refactor_without_errors(actions)

        # try to create an input for first_cat/input1 automatically
        actions = [
            {
                "action_type": "extract_input",
                "input": {"label": "first_cat", "input_name": "input1"},
                "label": "extracted_input",
            }
        ]
        self._refactor_without_errors(actions)
        assert self._latest_workflow.step_by_label("extracted_input")
        assert len(self._latest_workflow.step_by_label("first_cat").inputs) == 1

    def test_refactoring_legacy_parameters(self):
        wf = self.workflow_populator.load_workflow_from_resource("test_workflow_randomlines_legacy_params")
        self.workflow_populator.create_workflow(wf)
        actions = [
            {"action_type": "extract_legacy_parameter", "name": "seed"},
            {"action_type": "extract_legacy_parameter", "name": "num", "label": "renamed_num"},
        ]
        self._refactor_without_errors(actions)
        assert self._latest_workflow.step_by_label("seed").tool_inputs["parameter_type"] == "text"
        assert self._latest_workflow.step_by_label("renamed_num").tool_inputs["parameter_type"] == "integer"
        random_lines_state = self._latest_workflow.step_by_index(2).tool_inputs
        assert "num_lines" in random_lines_state
        num_lines = random_lines_state["num_lines"]
        assert isinstance(num_lines, dict)
        assert "__class__" in num_lines
        assert num_lines["__class__"] == 'ConnectedValue'
        assert "seed_source" in random_lines_state
        seed_source = random_lines_state["seed_source"]
        assert isinstance(seed_source, dict)
        assert "seed" in seed_source
        seed = seed_source["seed"]
        assert isinstance(seed, dict)
        assert "__class__" in seed
        assert seed["__class__"] == 'ConnectedValue'

        # cannot handle mixed, incompatible types on the inputs though
        wf = self.workflow_populator.load_workflow_from_resource("test_workflow_randomlines_legacy_params_mixed_types")
        self.workflow_populator.create_workflow(wf)
        actions = [
            {"action_type": "extract_legacy_parameter", "name": "mixed_param"},
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
        self.workflow_populator.upload_yaml_workflow("""
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
""")
        actions = [
            {"action_type": "extract_legacy_parameter", "name": "pja_only_param"},
        ]
        self._refactor_without_errors(actions)
        assert self._latest_workflow.step_by_label("pja_only_param").tool_inputs["parameter_type"] == "text"

    def test_refactoring_legacy_parameters_without_tool_state_relabel(self):
        # same thing as above, but apply relabeling and ensure PJA gets updated.
        self.workflow_populator.upload_yaml_workflow("""
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
""")
        actions = [
            {"action_type": "extract_legacy_parameter", "name": "pja_only_param", "label": "new_label"},
        ]
        self._refactor_without_errors(actions)
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
        self._refactor_without_errors(actions)
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
        self._refactor_without_errors(actions)
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
        updated, errors = self._refactor(actions)
        assert updated
        assert errors  # we have a "message" about the un-validated state, but I is fine as long as it was preserved
        assert self._latest_workflow.step_by_index(1).label == "random2_new"
        assert "num_lines" in self._latest_workflow.step_by_index(1).tool_inputs

    def _refactor_without_errors(self, actions):
        updated, errors = self._refactor(actions)
        assert updated
        assert not errors
        return updated

    def _refactor(self, actions):
        user = self._app.model.session.query(self._app.model.User).order_by(self._app.model.User.id.desc()).limit(1).one()
        mock_trans = MockTrans(self._app, user)
        return self._manager.refactor(
            mock_trans,
            self._most_recent_stored_workflow,
            RefactorRequest(**{"actions": actions})
        )

    @property
    def _manager(self):
        return self._app.workflow_contents_manager

    @property
    def _most_recent_stored_workflow(self):
        app = self._app
        model = app.model
        return app.model.session.query(app.model.StoredWorkflow).order_by(model.StoredWorkflow.id.desc()).limit(1).one()

    @property
    def _latest_workflow(self):
        return self._most_recent_stored_workflow.latest_workflow


class MockTrans(ProvidesAppContext):

    def __init__(self, app, user):
        self.app = app
        self.user = user
        self.history = None
