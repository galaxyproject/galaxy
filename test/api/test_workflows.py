from __future__ import print_function

import json
import time
from json import dumps
from uuid import uuid4

from requests import delete, get, put

from base import api  # noqa: I100,I202
from base import rules_test_data  # noqa: I100
from base.populators import (  # noqa: I100
    DatasetCollectionPopulator,
    DatasetPopulator,
    skip_without_tool,
    wait_on,
    WorkflowPopulator
)
from base.workflow_fixtures import (  # noqa: I100
    WORKFLOW_NESTED_REPLACEMENT_PARAMETER,
    WORKFLOW_NESTED_RUNTIME_PARAMETER,
    WORKFLOW_NESTED_SIMPLE,
    WORKFLOW_ONE_STEP_DEFAULT,
    WORKFLOW_RENAME_ON_INPUT,
    WORKFLOW_RUNTIME_PARAMETER_AFTER_PAUSE,
    WORKFLOW_WITH_DYNAMIC_OUTPUT_COLLECTION,
    WORKFLOW_WITH_OUTPUT_COLLECTION,
    WORKFLOW_WITH_OUTPUT_COLLECTION_MAPPING,
    WORKFLOW_WITH_RULES_1,
)
from galaxy.exceptions import error_codes  # noqa: I201


NESTED_WORKFLOW_AUTO_LABELS = """
class: GalaxyWorkflow
inputs:
  outer_input: data
outputs:
  outer_output:
    outputSource: second_cat/out_file1
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: outer_input
  nested_workflow:
    run:
      class: GalaxyWorkflow
      inputs:
        - id: inner_input
      outputs:
        - source: 1#out_file1
      steps:
        random:
          tool_id: random_lines1
          state:
            num_lines: 1
            input:
              $link: inner_input
            seed_source:
              seed_source_selector: set_seed
              seed: asdf
    in:
      inner_input: first_cat/out_file1
  second_cat:
    tool_id: cat1
    state:
      input1:
        $link: nested_workflow#1:out_file1
      queries:
        - input2:
            $link: nested_workflow#1:out_file1
"""


class BaseWorkflowsApiTestCase(api.ApiTestCase):
    # TODO: Find a new file for this class.

    def setUp(self):
        super(BaseWorkflowsApiTestCase, self).setUp()
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def _assert_user_has_workflow_with_name(self, name):
        names = self._workflow_names()
        assert name in names, "No workflows with name %s in users workflows <%s>" % (name, names)

    def _workflow_names(self):
        index_response = self._get("workflows")
        self._assert_status_code_is(index_response, 200)
        names = [w["name"] for w in index_response.json()]
        return names

    def import_workflow(self, workflow, **kwds):
        upload_response = self.workflow_populator.import_workflow(workflow, **kwds)
        return upload_response

    def _upload_yaml_workflow(self, has_yaml, **kwds):
        return self.workflow_populator.upload_yaml_workflow(has_yaml, **kwds)

    def _setup_workflow_run(self, workflow=None, inputs_by='step_id', history_id=None, workflow_id=None):
        if not workflow_id:
            workflow_id = self.workflow_populator.create_workflow(workflow)
        if not history_id:
            history_id = self.dataset_populator.new_history()
        hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
        hda2 = self.dataset_populator.new_dataset(history_id, content="4 5 6")
        workflow_request = dict(
            history="hist_id=%s" % history_id,
            workflow_id=workflow_id,
        )
        label_map = {
            'WorkflowInput1': self._ds_entry(hda1),
            'WorkflowInput2': self._ds_entry(hda2)
        }
        if inputs_by == 'step_id':
            ds_map = self._build_ds_map(workflow_id, label_map)
            workflow_request["ds_map"] = ds_map
        elif inputs_by == "step_index":
            index_map = {
                '0': self._ds_entry(hda1),
                '1': self._ds_entry(hda2)
            }
            workflow_request["inputs"] = dumps(index_map)
            workflow_request["inputs_by"] = 'step_index'
        elif inputs_by == "name":
            workflow_request["inputs"] = dumps(label_map)
            workflow_request["inputs_by"] = 'name'
        elif inputs_by in ["step_uuid", "uuid_implicitly"]:
            uuid_map = {
                workflow["steps"]["0"]["uuid"]: self._ds_entry(hda1),
                workflow["steps"]["1"]["uuid"]: self._ds_entry(hda2),
            }
            workflow_request["inputs"] = dumps(uuid_map)
            if inputs_by == "step_uuid":
                workflow_request["inputs_by"] = "step_uuid"

        return workflow_request, history_id

    def _build_ds_map(self, workflow_id, label_map):
        workflow_inputs = self._workflow_inputs(workflow_id)
        ds_map = {}
        for key, value in workflow_inputs.items():
            label = value["label"]
            if label in label_map:
                ds_map[key] = label_map[label]
        return dumps(ds_map)

    def _ds_entry(self, history_content):
        return self.dataset_populator.ds_entry(history_content)

    def _workflow_inputs(self, uploaded_workflow_id):
        workflow_show_resposne = self._get("workflows/%s" % uploaded_workflow_id)
        self._assert_status_code_is(workflow_show_resposne, 200)
        workflow_inputs = workflow_show_resposne.json()["inputs"]
        return workflow_inputs

    def _invocation_details(self, workflow_id, invocation_id, **kwds):
        invocation_details_response = self._get("workflows/%s/usage/%s" % (workflow_id, invocation_id), data=kwds)
        self._assert_status_code_is(invocation_details_response, 200)
        invocation_details = invocation_details_response.json()
        return invocation_details

    def _run_jobs(self, has_workflow, history_id=None, **kwds):
        if history_id is None:
            history_id = self.history_id

        return self.workflow_populator.run_workflow(has_workflow, history_id=history_id, **kwds)

    def _history_jobs(self, history_id):
        return self._get("jobs", {"history_id": history_id, "order_by": "create_time"}).json()

    def _assert_history_job_count(self, history_id, n):
        jobs = self._history_jobs(history_id)
        self.assertEqual(len(jobs), n)

    def _download_workflow(self, workflow_id, style=None):
        return self.workflow_populator.download_workflow(workflow_id, style=style)

    def wait_for_invocation_and_jobs(self, history_id, workflow_id, invocation_id, assert_ok=True):
        state = self.workflow_populator.wait_for_invocation(workflow_id, invocation_id)
        if assert_ok:
            assert state == "scheduled", state
        self.workflow_populator.wait_for_invocation(workflow_id, invocation_id)
        time.sleep(.5)
        self.dataset_populator.wait_for_history_jobs(history_id, assert_ok=assert_ok)
        time.sleep(.5)

    def _assert_is_runtime_input(self, tool_state_value):
        if not isinstance(tool_state_value, dict):
            tool_state_value = json.loads(tool_state_value)

        assert isinstance(tool_state_value, dict)
        assert "__class__" in tool_state_value
        assert tool_state_value["__class__"] == "RuntimeValue"


# Workflow API TODO:
# - Allow history_id as param to workflow run action. (hist_id)
# - Allow post to workflows/<workflow_id>/run in addition to posting to
#    /workflows with id in payload.
# - Much more testing obviously, always more testing.
class WorkflowsApiTestCase(BaseWorkflowsApiTestCase):

    def setUp(self):
        super(WorkflowsApiTestCase, self).setUp()

    def test_show_valid(self):
        workflow_id = self.workflow_populator.simple_workflow("dummy")
        workflow_id = self.workflow_populator.simple_workflow("test_regular")
        show_response = self._get("workflows/%s" % workflow_id, {"style": "instance"})
        workflow = show_response.json()
        self._assert_looks_like_instance_workflow_representation(workflow)
        assert len(workflow["steps"]) == 3
        self.assertEqual(sorted(step["id"] for step in workflow["steps"].values()), [0, 1, 2])

        show_response = self._get("workflows/%s" % workflow_id, {"legacy": True})
        workflow = show_response.json()
        self._assert_looks_like_instance_workflow_representation(workflow)
        assert len(workflow["steps"]) == 3
        # Can't reay say what the legacy IDs are but must be greater than 3 because dummy
        # workflow was created first in this instance.
        self.assertNotEqual(sorted(step["id"] for step in workflow["steps"].values()), [0, 1, 2])

    def test_show_invalid_key_is_400(self):
        show_response = self._get("workflows/%s" % self._random_key())
        self._assert_status_code_is(show_response, 400)

    def test_cannot_show_private_workflow(self):
        workflow_id = self.workflow_populator.simple_workflow("test_not_importportable")
        with self._different_user():
            show_response = self._get("workflows/%s" % workflow_id)
            self._assert_status_code_is(show_response, 403)

            # Try as anonymous user
            workflows_url = self._api_url("workflows/%s" % workflow_id)
            assert get(workflows_url).status_code == 403

    def test_delete(self):
        workflow_id = self.workflow_populator.simple_workflow("test_delete")
        workflow_name = "test_delete"
        self._assert_user_has_workflow_with_name(workflow_name)
        workflow_url = self._api_url("workflows/%s" % workflow_id, use_key=True)
        delete_response = delete(workflow_url)
        self._assert_status_code_is(delete_response, 200)
        # Make sure workflow is no longer in index by default.
        assert workflow_name not in self._workflow_names()

    def test_other_cannot_delete(self):
        workflow_id = self.workflow_populator.simple_workflow("test_other_delete")
        with self._different_user():
            workflow_url = self._api_url("workflows/%s" % workflow_id, use_key=True)
            delete_response = delete(workflow_url)
            self._assert_status_code_is(delete_response, 403)

    def test_index(self):
        index_response = self._get("workflows")
        self._assert_status_code_is(index_response, 200)
        assert isinstance(index_response.json(), list)

    def test_upload(self):
        self.__test_upload(use_deprecated_route=False)

    def test_upload_deprecated(self):
        self.__test_upload(use_deprecated_route=True)

    def test_import_tools_requires_admin(self):
        response = self.__test_upload(import_tools=True, assert_ok=False)
        assert response.status_code == 403

    def __test_upload(self, use_deprecated_route=False, name="test_import", workflow=None, assert_ok=True, import_tools=False):
        if workflow is None:
            workflow = self.workflow_populator.load_workflow(name=name)
        data = dict(
            workflow=dumps(workflow),
        )
        if import_tools:
            data["import_tools"] = import_tools
        if use_deprecated_route:
            route = "workflows/upload"
        else:
            route = "workflows"
        upload_response = self._post(route, data=data)
        if assert_ok:
            self._assert_status_code_is(upload_response, 200)
            self._assert_user_has_workflow_with_name(name)
        return upload_response

    def test_update(self):
        original_workflow = self.workflow_populator.load_workflow(name="test_import")
        uuids = {}
        labels = {}

        for order_index, step_dict in original_workflow["steps"].items():
            uuid = str(uuid4())
            step_dict["uuid"] = uuid
            uuids[order_index] = uuid
            label = "label_%s" % order_index
            step_dict["label"] = label
            labels[order_index] = label

        def check_label_and_uuid(order_index, step_dict):
            assert order_index in uuids
            assert order_index in labels

            self.assertEqual(uuids[order_index], step_dict["uuid"])
            self.assertEqual(labels[order_index], step_dict["label"])

        upload_response = self.__test_upload(workflow=original_workflow)
        workflow_id = upload_response.json()["id"]

        def update(workflow_object):
            put_response = self._update_workflow(workflow_id, workflow_object)
            self._assert_status_code_is(put_response, 200)
            return put_response

        workflow_content = self._download_workflow(workflow_id)
        steps = workflow_content["steps"]

        def tweak_step(step):
            order_index, step_dict = step
            check_label_and_uuid(order_index, step_dict)
            assert step_dict['position']['top'] != 1
            assert step_dict['position']['left'] != 1
            step_dict['position'] = {'top': 1, 'left': 1}

        map(tweak_step, steps.items())

        update(workflow_content)

        def check_step(step):
            order_index, step_dict = step
            check_label_and_uuid(order_index, step_dict)
            assert step_dict['position']['top'] == 1
            assert step_dict['position']['left'] == 1

        updated_workflow_content = self._download_workflow(workflow_id)
        map(check_step, updated_workflow_content['steps'].items())

        # Re-update against original workflow...
        update(original_workflow)

        updated_workflow_content = self._download_workflow(workflow_id)

        # Make sure the positions have been updated.
        map(tweak_step, updated_workflow_content['steps'].items())

    def test_update_no_tool_id(self):
        workflow_object = self.workflow_populator.load_workflow(name="test_import")
        upload_response = self.__test_upload(workflow=workflow_object)
        workflow_id = upload_response.json()["id"]
        del workflow_object["steps"]["2"]["tool_id"]
        put_response = self._update_workflow(workflow_id, workflow_object)
        self._assert_status_code_is(put_response, 400)

    def test_update_missing_tool(self):
        # Create allows missing tools, update doesn't currently...
        workflow_object = self.workflow_populator.load_workflow(name="test_import")
        upload_response = self.__test_upload(workflow=workflow_object)
        workflow_id = upload_response.json()["id"]
        workflow_object["steps"]["2"]["tool_id"] = "cat-not-found"
        put_response = self._update_workflow(workflow_id, workflow_object)
        self._assert_status_code_is(put_response, 400)

    def test_require_unique_step_uuids(self):
        workflow_dup_uuids = self.workflow_populator.load_workflow(name="test_import")
        uuid0 = str(uuid4())
        for step_dict in workflow_dup_uuids["steps"].values():
            step_dict["uuid"] = uuid0
        response = self.workflow_populator.create_workflow_response(workflow_dup_uuids)
        self._assert_status_code_is(response, 400)

    def test_require_unique_step_labels(self):
        workflow_dup_label = self.workflow_populator.load_workflow(name="test_import")
        for step_dict in workflow_dup_label["steps"].values():
            step_dict["label"] = "my duplicated label"
        response = self.workflow_populator.create_workflow_response(workflow_dup_label)
        self._assert_status_code_is(response, 400)

    def test_import_deprecated(self):
        workflow_id = self.workflow_populator.simple_workflow("test_import_published_deprecated", publish=True)
        with self._different_user():
            other_import_response = self.__import_workflow(workflow_id)
            self._assert_status_code_is(other_import_response, 200)
            self._assert_user_has_workflow_with_name("imported: test_import_published_deprecated")

    def test_import_annotations(self):
        workflow_id = self.workflow_populator.simple_workflow("test_import_annotations", publish=True)
        with self._different_user():
            other_import_response = self.__import_workflow(workflow_id)
            self._assert_status_code_is(other_import_response, 200)

            # Test annotations preserved during upload and copied over during
            # import.
            other_id = other_import_response.json()["id"]
            imported_workflow = self._show_workflow(other_id)
            assert imported_workflow["annotation"] == "simple workflow"
            step_annotations = set(step["annotation"] for step in imported_workflow["steps"].values())
            assert "input1 description" in step_annotations

    def test_import_subworkflows(self):
        def get_subworkflow_content_id(workflow_id):
            workflow_contents = self._download_workflow(workflow_id, style="editor")
            steps = workflow_contents['steps']
            subworkflow_step = next(s for s in steps.values() if s["type"] == "subworkflow")
            return subworkflow_step['content_id']

        workflow_id = self._upload_yaml_workflow(WORKFLOW_NESTED_SIMPLE, publish=True)
        subworkflow_content_id = get_subworkflow_content_id(workflow_id)
        with self._different_user():
            other_import_response = self.__import_workflow(workflow_id)
            self._assert_status_code_is(other_import_response, 200)
            imported_workflow_id = other_import_response.json()["id"]
            imported_subworkflow_content_id = get_subworkflow_content_id(imported_workflow_id)
            assert subworkflow_content_id != imported_subworkflow_content_id

    def test_not_importable_prevents_import(self):
        workflow_id = self.workflow_populator.simple_workflow("test_not_importportable")
        with self._different_user():
            other_import_response = self.__import_workflow(workflow_id)
            self._assert_status_code_is(other_import_response, 403)

    def test_anonymous_published(self):
        def anonymous_published_workflows():
            workflows_url = self._api_url("workflows?show_published=True")
            return get(workflows_url).json()

        names = [w["name"] for w in anonymous_published_workflows()]
        assert "test published example" not in names
        workflow_id = self.workflow_populator.simple_workflow("test published example", publish=True)

        names = [w["name"] for w in anonymous_published_workflows()]
        assert "test published example" in names
        ids = [w["id"] for w in anonymous_published_workflows()]
        assert workflow_id in ids

    def test_import_published(self):
        workflow_id = self.workflow_populator.simple_workflow("test_import_published", publish=True)
        with self._different_user():
            other_import_response = self.__import_workflow(workflow_id, deprecated_route=True)
            self._assert_status_code_is(other_import_response, 200)
            self._assert_user_has_workflow_with_name("imported: test_import_published")

    def test_export(self):
        uploaded_workflow_id = self.workflow_populator.simple_workflow("test_for_export")
        downloaded_workflow = self._download_workflow(uploaded_workflow_id)
        assert downloaded_workflow["name"] == "test_for_export"
        assert len(downloaded_workflow["steps"]) == 3
        first_input = downloaded_workflow["steps"]["0"]["inputs"][0]
        assert first_input["name"] == "WorkflowInput1"
        assert first_input["description"] == "input1 description"
        self._assert_has_keys(downloaded_workflow, "a_galaxy_workflow", "format-version", "annotation", "uuid", "steps")
        for step in downloaded_workflow["steps"].values():
            self._assert_has_keys(
                step,
                'id',
                'type',
                'tool_id',
                'tool_version',
                'name',
                'tool_state',
                'annotation',
                'inputs',
                'workflow_outputs',
                'outputs'
            )
            if step['type'] == "tool":
                self._assert_has_keys(step, "post_job_actions")

    def test_export_editor(self):
        uploaded_workflow_id = self.workflow_populator.simple_workflow("test_for_export")
        downloaded_workflow = self._download_workflow(uploaded_workflow_id, style="editor")
        self._assert_has_keys(downloaded_workflow, "name", "steps", "upgrade_messages")
        for step in downloaded_workflow["steps"].values():
            self._assert_has_keys(
                step,
                'id',
                'type',
                'content_id',
                'name',
                'tool_state',
                'tooltip',
                'inputs',
                'outputs',
                'config_form',
                'annotation',
                'post_job_actions',
                'workflow_outputs',
                'uuid',
                'label',
            )

    @skip_without_tool('collection_type_source')
    def test_export_editor_collection_type_source(self):
        workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
inputs:
  - id: text_input1
    type: collection
    collection_type: "list:paired"
steps:
  - tool_id: collection_type_source
    in:
      input_collect: text_input1
""")
        downloaded_workflow = self._download_workflow(workflow_id, style="editor")
        steps = downloaded_workflow['steps']
        assert len(steps) == 2
        # Non-subworkflow collection_type_source tools will be handled by the client,
        # so collection_type should be None here.
        assert steps['1']['outputs'][0]['collection_type'] is None

    @skip_without_tool('collection_type_source')
    def test_export_editor_subworkflow_collection_type_source(self):
        workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
inputs:
  outer_input: data
steps:
  inner_workflow:
    run:
      class: GalaxyWorkflow
      inputs:
        inner_input:
          type: collection
          collection_type: "list:paired"
      outputs:
        workflow_output:
          outputSource: collection_type_source/list_output
      steps:
        collection_type_source:
          tool_id: collection_type_source
          in:
            input_collect: inner_input
    in:
      inner_input: outer_input
""")
        downloaded_workflow = self._download_workflow(workflow_id, style="editor")
        steps = downloaded_workflow['steps']
        assert len(steps) == 2
        assert steps['1']['type'] == 'subworkflow'
        assert steps['1']['outputs'][0]['collection_type'] == 'list:paired'

    def test_import_missing_tool(self):
        workflow = self.workflow_populator.load_workflow_from_resource(name="test_workflow_missing_tool")
        workflow_id = self.workflow_populator.create_workflow(workflow)
        workflow_description = self._show_workflow(workflow_id)
        steps = workflow_description["steps"]
        missing_tool_steps = [v for v in steps.values() if v['tool_id'] == 'cat_missing_tool']
        assert len(missing_tool_steps) == 1

    def test_import_no_tool_id(self):
        # Import works with missing tools, but not with absent content/tool id.
        workflow = self.workflow_populator.load_workflow_from_resource(name="test_workflow_missing_tool")
        del workflow["steps"]["2"]["tool_id"]
        create_response = self.__test_upload(workflow=workflow, assert_ok=False)
        self._assert_status_code_is(create_response, 400)

    def test_import_export_with_runtime_inputs(self):
        workflow = self.workflow_populator.load_workflow_from_resource(name="test_workflow_with_runtime_input")
        workflow_id = self.workflow_populator.create_workflow(workflow)
        downloaded_workflow = self._download_workflow(workflow_id)
        assert len(downloaded_workflow["steps"]) == 2
        runtime_step = downloaded_workflow["steps"]["1"]
        for runtime_input in runtime_step["inputs"]:
            if runtime_input["name"] == "num_lines":
                break

        assert runtime_input["description"].startswith("runtime parameter for tool")

        tool_state = json.loads(runtime_step["tool_state"])
        assert "num_lines" in tool_state
        self._assert_is_runtime_input(tool_state["num_lines"])

    @skip_without_tool("cat1")
    def test_run_workflow_by_index(self):
        self.__run_cat_workflow(inputs_by='step_index')

    @skip_without_tool("cat1")
    def test_run_workflow_by_uuid(self):
        self.__run_cat_workflow(inputs_by='step_uuid')

    @skip_without_tool("cat1")
    def test_run_workflow_by_uuid_implicitly(self):
        self.__run_cat_workflow(inputs_by='uuid_implicitly')

    @skip_without_tool("cat1")
    def test_run_workflow_by_name(self):
        self.__run_cat_workflow(inputs_by='name')

    @skip_without_tool("cat1")
    def test_run_workflow(self):
        self.__run_cat_workflow(inputs_by='step_id')

    @skip_without_tool("multiple_versions")
    def test_run_versioned_tools(self):
        with self.dataset_populator.test_history() as history_01_id:
            workflow_version_01 = self._upload_yaml_workflow("""
class: GalaxyWorkflow
steps:
  multiple:
    tool_id: multiple_versions
    tool_version: "0.1"
    state:
      inttest: 0
""")
            self.__invoke_workflow(history_01_id, workflow_version_01)
            self.dataset_populator.wait_for_history(history_01_id, assert_ok=True)

        with self.dataset_populator.test_history() as history_02_id:
            workflow_version_02 = self._upload_yaml_workflow("""
class: GalaxyWorkflow
steps:
  multiple:
    tool_id: multiple_versions
    tool_version: "0.2"
    state:
      inttest: 1
""")
            self.__invoke_workflow(history_02_id, workflow_version_02)
            self.dataset_populator.wait_for_history(history_02_id, assert_ok=True)

    def __run_cat_workflow(self, inputs_by):
        workflow = self.workflow_populator.load_workflow(name="test_for_run")
        workflow["steps"]["0"]["uuid"] = str(uuid4())
        workflow["steps"]["1"]["uuid"] = str(uuid4())
        workflow_request, history_id = self._setup_workflow_run(workflow, inputs_by=inputs_by)
        # TODO: This should really be a post to workflows/<workflow_id>/run or
        # something like that.
        run_workflow_response = self._post("workflows", data=workflow_request)
        self._assert_status_code_is(run_workflow_response, 200)
        invocation_id = run_workflow_response.json()["id"]
        invocation = self._invocation_details(workflow_request["workflow_id"], invocation_id)
        assert invocation["state"] == "scheduled", invocation

        self._assert_status_code_is(run_workflow_response, 200)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)

    @skip_without_tool("collection_creates_pair")
    def test_workflow_run_output_collections(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(WORKFLOW_WITH_OUTPUT_COLLECTION, history_id=history_id, assert_ok=True, wait=True)
            self.assertEqual("a\nc\nb\nd\n", self.dataset_populator.get_history_dataset_content(history_id, hid=0))

    @skip_without_tool("job_properties")
    @skip_without_tool("identifier_multiple_in_conditional")
    def test_workflow_resume_from_failed_step(self):
        workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
steps:
  job_props:
    tool_id: job_properties
    state:
      thebool: true
      failbool: true
  identifier:
    tool_id: identifier_multiple_in_conditional
    state:
      outer_cond:
        cond_param_outer: true
        inner_cond:
          cond_param_inner: true
          input1:
            $link: 0#out_file1
""")
        with self.dataset_populator.test_history() as history_id:
            invocation_id = self.__invoke_workflow(history_id, workflow_id)
            self.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id, assert_ok=False)
            failed_dataset_one = self.dataset_populator.get_history_dataset_details(history_id, hid=1, wait=True, assert_ok=False)
            assert failed_dataset_one['state'] == 'error', failed_dataset_one
            paused_dataset = self.dataset_populator.get_history_dataset_details(history_id, hid=5, wait=True, assert_ok=False)
            assert paused_dataset['state'] == 'paused', paused_dataset
            inputs = {"thebool": "false",
                      "failbool": "false",
                      "rerun_remap_job_id": failed_dataset_one['creating_job']}
            self.dataset_populator.run_tool(tool_id='job_properties',
                                            inputs=inputs,
                                            history_id=history_id,
                                            assert_ok=True)
            unpaused_dataset = self.dataset_populator.get_history_dataset_details(history_id, hid=5, wait=True, assert_ok=False)
            assert unpaused_dataset['state'] == 'ok'

    @skip_without_tool("job_properties")
    @skip_without_tool("identifier_collection")
    def test_workflow_resume_from_failed_step_with_hdca_input(self):
        workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
steps:
  job_props:
    tool_id: job_properties
    state:
      thebool: true
      failbool: true
  identifier:
    tool_id: identifier_collection
    in:
      input1: job_props/list_output
""")
        with self.dataset_populator.test_history() as history_id:
            invocation_id = self.__invoke_workflow(history_id, workflow_id)
            self.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id, assert_ok=False)
            failed_dataset_one = self.dataset_populator.get_history_dataset_details(history_id, hid=1, wait=True, assert_ok=False)
            assert failed_dataset_one['state'] == 'error', failed_dataset_one
            paused_dataset = self.dataset_populator.get_history_dataset_details(history_id, hid=5, wait=True, assert_ok=False)
            assert paused_dataset['state'] == 'paused', paused_dataset
            inputs = {"thebool": "false",
                      "failbool": "false",
                      "rerun_remap_job_id": failed_dataset_one['creating_job']}
            self.dataset_populator.run_tool(tool_id='job_properties',
                                            inputs=inputs,
                                            history_id=history_id,
                                            assert_ok=True)
            unpaused_dataset = self.dataset_populator.get_history_dataset_details(history_id, hid=5, wait=True,
                                                                                  assert_ok=False)
            assert unpaused_dataset['state'] == 'ok'

    @skip_without_tool("fail_identifier")
    @skip_without_tool("identifier_collection")
    def test_workflow_resume_with_mapped_over_input(self):
        with self.dataset_populator.test_history() as history_id:
            job_summary = self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input_datasets: collection
steps:
  fail_identifier_1:
    tool_id: fail_identifier
    state:
      failbool: true
    in:
      input1: input_datasets
  identifier:
    tool_id: identifier_collection
    in:
      input1: fail_identifier_1/out_file1
test_data:
  input_datasets:
    type: list
    elements:
      - identifier: fail
        value: 1.fastq
        type: File
      - identifier: success
        value: 1.fastq
        type: File
""", history_id=history_id, assert_ok=False, wait=False)
            self.wait_for_invocation_and_jobs(history_id, job_summary.workflow_id, job_summary.invocation_id, assert_ok=False)
            history_contents = self.dataset_populator._get_contents_request(history_id=history_id).json()
            paused_dataset = history_contents[-1]
            failed_dataset = self.dataset_populator.get_history_dataset_details(history_id, hid=5, assert_ok=False)
            assert paused_dataset['state'] == 'paused', paused_dataset
            assert failed_dataset['state'] == 'error', failed_dataset
            inputs = {"input1": {'values': [{'src': 'hda',
                                             'id': history_contents[0]['id']}]
                                 },
                      "failbool": "false",
                      "rerun_remap_job_id": failed_dataset['creating_job']}
            run_dict = self.dataset_populator.run_tool(tool_id='fail_identifier',
                                                       inputs=inputs,
                                                       history_id=history_id,
                                                       assert_ok=True)
            unpaused_dataset = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=False)
            assert unpaused_dataset['state'] == 'ok'
            contents = self.dataset_populator.get_history_dataset_content(history_id, hid=7, assert_ok=False)
            assert contents == 'fail\nsuccess\n', contents
            replaced_hda_id = run_dict['outputs'][0]['id']
            replaced_hda = self.dataset_populator.get_history_dataset_details(history_id, dataset_id=replaced_hda_id, wait=True, assert_ok=False)
            assert not replaced_hda['visible'], replaced_hda

    @skip_without_tool('multi_data_optional')
    def test_workflow_list_list_multi_data_map_over(self):
        # Test that a list:list is reduced to list with a multiple="true" data input
        with self.dataset_populator.test_history() as history_id:
            workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
inputs:
  input_datasets: collection
steps:
  multi_data_optional:
    tool_id: multi_data_optional
    in:
      input1: input_datasets
""")
            with self.dataset_populator.test_history() as history_id:
                hdca_id = self.dataset_collection_populator.create_list_of_list_in_history(history_id).json()
                self.dataset_populator.wait_for_history(history_id, assert_ok=True)
                inputs = {
                    '0': self._ds_entry(hdca_id),
                }
                invocation_id = self.__invoke_workflow(history_id, workflow_id, inputs)
                self.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)
                output_collection = self.dataset_populator.get_history_collection_details(history_id, hid=6)
                assert output_collection['collection_type'] == 'list'
                assert output_collection['job_source_type'] == 'ImplicitCollectionJobs'

    @skip_without_tool("cat_list")
    @skip_without_tool("collection_creates_pair")
    def test_workflow_run_output_collection_mapping(self):
        workflow_id = self._upload_yaml_workflow(WORKFLOW_WITH_OUTPUT_COLLECTION_MAPPING)
        with self.dataset_populator.test_history() as history_id:
            hdca1 = self.dataset_collection_populator.create_list_in_history(history_id, contents=["a\nb\nc\nd\n", "e\nf\ng\nh\n"]).json()
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            inputs = {
                '0': self._ds_entry(hdca1),
            }
            invocation_id = self.__invoke_workflow(history_id, workflow_id, inputs)
            self.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)
            self.assertEqual("a\nc\nb\nd\ne\ng\nf\nh\n", self.dataset_populator.get_history_dataset_content(history_id, hid=0))

    @skip_without_tool("cat_list")
    @skip_without_tool("collection_split_on_column")
    def test_workflow_run_dynamic_output_collections(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(WORKFLOW_WITH_DYNAMIC_OUTPUT_COLLECTION, history_id=history_id, assert_ok=True, wait=True)
            details = self.dataset_populator.get_history_dataset_details(history_id, hid=0)
            last_item_hid = details["hid"]
            assert last_item_hid == 7, "Expected 7 history items, got %s" % last_item_hid
            content = self.dataset_populator.get_history_dataset_content(history_id, hid=0)
            self.assertEqual("10.0\n30.0\n20.0\n40.0\n", content)

    @skip_without_tool("collection_split_on_column")
    @skip_without_tool("min_repeat")
    def test_workflow_run_dynamic_output_collections_2(self):
        # A more advanced output collection workflow, testing regression of
        # https://github.com/galaxyproject/galaxy/issues/776
        with self.dataset_populator.test_history() as history_id:
            workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
inputs:
  test_input_1: data
  test_input_2: data
  test_input_3: data
steps:
  split_up:
    tool_id: collection_split_on_column
    in:
      input1: test_input_2
  min_repeat:
    tool_id: min_repeat
    in:
      queries_0|input: test_input_1
      queries2_0|input2: split_up/split_output
""")
            hda1 = self.dataset_populator.new_dataset(history_id, content="samp1\t10.0\nsamp2\t20.0\n")
            hda2 = self.dataset_populator.new_dataset(history_id, content="samp1\t20.0\nsamp2\t40.0\n")
            hda3 = self.dataset_populator.new_dataset(history_id, content="samp1\t30.0\nsamp2\t60.0\n")
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            inputs = {
                '0': self._ds_entry(hda1),
                '1': self._ds_entry(hda2),
                '2': self._ds_entry(hda3),
            }
            invocation_id = self.__invoke_workflow(history_id, workflow_id, inputs)
            self.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)
            collection_details = self.dataset_populator.get_history_collection_details(history_id, hid=7)
            assert collection_details["populated_state"] == "ok"
            content = self.dataset_populator.get_history_dataset_content(history_id, hid=11)
            self.assertEqual(content.strip(), "samp1\t10.0\nsamp2\t20.0")

    @skip_without_tool("cat")
    @skip_without_tool("collection_split_on_column")
    def test_workflow_run_dynamic_output_collections_3(self):
        # Test a workflow that create a list:list:list followed by a mapping step.
        with self.dataset_populator.test_history() as history_id:
            workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
inputs:
  text_input1: data
  text_input2: data
steps:
  cat_inputs:
    tool_id: cat1
    in:
      input1: text_input1
      queries_0|input2: text_input2
  split_up_1:
    tool_id: collection_split_on_column
    in:
      input1: cat_inputs/out_file1
  split_up_2:
    tool_id: collection_split_on_column
    in:
      input1: split_up_1/split_output
  cat_output:
    tool_id: cat
    in:
      input1: split_up_2/split_output
""")
            hda1 = self.dataset_populator.new_dataset(history_id, content="samp1\t10.0\nsamp2\t20.0\n")
            hda2 = self.dataset_populator.new_dataset(history_id, content="samp1\t30.0\nsamp2\t40.0\n")
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            inputs = {
                '0': self._ds_entry(hda1),
                '1': self._ds_entry(hda2),
            }
            invocation_id = self.__invoke_workflow(history_id, workflow_id, inputs)
            self.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)

    @skip_without_tool("mapper")
    @skip_without_tool("pileup")
    def test_workflow_metadata_validation_0(self):
        # Testing regression of
        # https://github.com/galaxyproject/galaxy/issues/1514
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input_fastqs: collection
  reference: data
steps:
  map_over_mapper:
    tool_id: mapper
    in:
      input1: input_fastqs
      reference: reference
  pileup:
    tool_id: pileup
    in:
      input1: map_over_mapper/out_file1
      reference: reference
test_data:
  input_fastqs:
    type: list
    elements:
      - identifier: samp1
        value: 1.fastq
        type: File
      - identifier: samp2
        value: 1.fastq
        type: File
  reference:
    value: 1.fasta
    type: File
""", history_id=history_id)

    def test_run_subworkflow_simple(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(WORKFLOW_NESTED_SIMPLE, test_data="""
outer_input:
  value: 1.bed
  type: File
""", history_id=history_id)

            content = self.dataset_populator.get_history_dataset_content(history_id)
            self.assertEqual("chrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\nchrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\n", content)

    @skip_without_tool("random_lines1")
    def test_run_subworkflow_runtime_parameters(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(WORKFLOW_NESTED_RUNTIME_PARAMETER, test_data="""
step_parameters:
  '1':
    '1|num_lines': 2
outer_input:
  value: 1.bed
  type: File
""", history_id=history_id)

            content = self.dataset_populator.get_history_dataset_content(history_id)
            assert len([x for x in content.split("\n") if x]) == 2

    @skip_without_tool("cat")
    def test_run_subworkflow_replacment_parameters(self):
        with self.dataset_populator.test_history() as history_id:
            test_data = """
replacement_parameters:
  replaceme: moocow
outer_input:
  value: 1.bed
  type: File
"""
            self._run_jobs(WORKFLOW_NESTED_REPLACEMENT_PARAMETER, test_data=test_data, history_id=history_id)
            details = self.dataset_populator.get_history_dataset_details(history_id)
            assert details["name"] == "moocow suffix"

    @skip_without_tool("random_lines1")
    def test_run_runtime_parameters_after_pause(self):
        with self.dataset_populator.test_history() as history_id:
            workflow_run_description = """%s

test_data:
  step_parameters:
    '2':
      'num_lines': 2
  input1:
    value: 1.bed
    type: File
""" % WORKFLOW_RUNTIME_PARAMETER_AFTER_PAUSE
            job_summary = self._run_jobs(workflow_run_description, history_id=history_id, wait=False)
            uploaded_workflow_id, invocation_id = job_summary.workflow_id, job_summary.invocation_id

            # Wait for at least one scheduling step.
            self._wait_for_invocation_non_new(uploaded_workflow_id, invocation_id)

            # Make sure the history didn't enter a failed state in there.
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            # Assert the workflow hasn't finished scheduling, we can be pretty sure we
            # are at the pause step in this case then.
            self._assert_invocation_non_terminal(uploaded_workflow_id, invocation_id)

            # Review the paused steps to allow the workflow to continue.
            self.__review_paused_steps(uploaded_workflow_id, invocation_id, order_index=1, action=True)

            # Wait for the workflow to finish scheduling and ensure both the invocation
            # and the history are in valid states.
            invocation_scheduled = self._wait_for_invocation_state(uploaded_workflow_id, invocation_id, 'scheduled')
            assert invocation_scheduled, "Workflow state is not scheduled..."
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            content = self.dataset_populator.get_history_dataset_content(history_id)
            assert len([x for x in content.split("\n") if x]) == 2

    def test_run_subworkflow_auto_labels(self):
        history_id = self.dataset_populator.new_history()
        test_data = """
outer_input:
  value: 1.bed
  type: File
"""
        job_summary = self._run_jobs(NESTED_WORKFLOW_AUTO_LABELS, test_data=test_data, history_id=history_id)
        assert len(job_summary.jobs) == 4, "4 jobs expected, got %d jobs" % len(job_summary.jobs)

        content = self.dataset_populator.get_history_dataset_content(history_id)
        self.assertEqual(
            "chrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\nchrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\n",
            content)

    @skip_without_tool("cat1")
    @skip_without_tool("collection_paired_test")
    def test_workflow_run_zip_collections(self):
        with self.dataset_populator.test_history() as history_id:
            workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
inputs:
  test_input_1: data
  test_input_2: data
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: test_input_1
  zip_it:
    tool_id: "__ZIP_COLLECTION__"
    in:
      input_forward: first_cat/out_file1
      input_reverse: test_input_2
  concat_pair:
    tool_id: collection_paired_test
    in:
      f1: zip_it/output
""")
            hda1 = self.dataset_populator.new_dataset(history_id, content="samp1\t10.0\nsamp2\t20.0\n")
            hda2 = self.dataset_populator.new_dataset(history_id, content="samp1\t20.0\nsamp2\t40.0\n")
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            inputs = {
                '0': self._ds_entry(hda1),
                '1': self._ds_entry(hda2),
            }
            invocation_id = self.__invoke_workflow(history_id, workflow_id, inputs)
            self.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)
            content = self.dataset_populator.get_history_dataset_content(history_id)
            self.assertEqual(content.strip(), "samp1\t10.0\nsamp2\t20.0\nsamp1\t20.0\nsamp2\t40.0")

    @skip_without_tool("collection_paired_test")
    def test_workflow_flatten(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
steps:
  nested:
    tool_id: collection_creates_dynamic_nested
    state:
      sleep_time: 0
      foo: 'dummy'
  flatten:
    tool_id: '__FLATTEN__'
    state:
      input:
        $link: nested#list_output
      join_identifier: '-'
""", test_data={}, history_id=history_id)
            details = self.dataset_populator.get_history_collection_details(history_id, hid=14)
            assert details['collection_type'] == "list"
            elements = details["elements"]
            identifiers = [e['element_identifier'] for e in elements]
            assert len(identifiers) == 6
            assert "oe1-ie1" in identifiers

    @skip_without_tool("__APPLY_RULES__")
    def test_workflow_run_apply_rules(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(WORKFLOW_WITH_RULES_1, history_id=history_id, wait=True, assert_ok=True, round_trip_format_conversion=True)
            output_content = self.dataset_populator.get_history_collection_details(history_id, hid=6)
            rules_test_data.check_example_2(output_content, self.dataset_populator)

    def test_filter_failed_mapping(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input_c: collection

steps:
  mixed_collection:
    tool_id: exit_code_from_file
    state:
       input:
         $link: input_c

  filtered_collection:
    tool_id: "__FILTER_FAILED_DATASETS__"
    state:
      input:
        $link: mixed_collection#out_file1

  cat:
    tool_id: cat1
    state:
      input1:
        $link: filtered_collection
""", test_data="""
input_c:
  type: list
  elements:
    - identifier: i1
      content: "0"
    - identifier: i2
      content: "1"
""", history_id=history_id, wait=True, assert_ok=False)
            jobs = summary.jobs

            def filter_jobs_by_tool(tool_id):
                return [j for j in summary.jobs if j["tool_id"] == tool_id]

            assert len(filter_jobs_by_tool("__DATA_FETCH__")) == 1, jobs
            assert len(filter_jobs_by_tool("exit_code_from_file")) == 2, jobs
            assert len(filter_jobs_by_tool("__FILTER_FAILED_DATASETS__")) == 1, jobs
            # Follow proves one job was filtered out of the result of cat1
            assert len(filter_jobs_by_tool("cat1")) == 1, jobs

    def test_workflow_request(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_queue")
        workflow_request, history_id = self._setup_workflow_run(workflow)
        url = "workflows/%s/usage" % (workflow_request["workflow_id"])
        del workflow_request["workflow_id"]
        run_workflow_response = self._post(url, data=workflow_request)

        self._assert_status_code_is(run_workflow_response, 200)
        # Give some time for workflow to get scheduled before scanning the history.
        time.sleep(5)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)

    def test_workflow_output_dataset(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1: data
outputs:
  wf_output_1:
    outputSource: first_cat/out_file1
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: input1
""", test_data={"input1": "hello world"}, history_id=history_id)
            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            invocation_response = self._get("workflows/%s/invocations/%s" % (workflow_id, invocation_id))
            self._assert_status_code_is(invocation_response, 200)
            invocation = invocation_response.json()
            self._assert_has_keys(invocation , "id", "outputs", "output_collections")
            assert len(invocation["output_collections"]) == 0
            assert len(invocation["outputs"]) == 1
            output_content = self.dataset_populator.get_history_dataset_content(history_id, dataset_id=invocation["outputs"]["wf_output_1"]["id"])
            assert "hello world" == output_content.strip()

    @skip_without_tool("cat")
    def test_workflow_output_dataset_collection(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1:
    type: data_collection_input
    collection_type: list
outputs:
  wf_output_1:
    outputSource: first_cat/out_file1
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input1
""", test_data="""
input1:
  type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
""", history_id=history_id, round_trip_format_conversion=True)
            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            invocation_response = self._get("workflows/%s/invocations/%s" % (workflow_id, invocation_id))
            self._assert_status_code_is(invocation_response, 200)
            invocation = invocation_response.json()
            self._assert_has_keys(invocation , "id", "outputs", "output_collections")
            assert len(invocation["output_collections"]) == 1
            assert len(invocation["outputs"]) == 0
            output_content = self.dataset_populator.get_history_collection_details(history_id, content_id=invocation["output_collections"]["wf_output_1"]["id"])
            self._assert_has_keys(output_content , "id", "elements")
            assert output_content["collection_type"] == "list"
            elements = output_content["elements"]
            assert len(elements) == 1
            elements0 = elements[0]
            assert elements0["element_identifier"] == "el1"

    def test_workflow_input_as_output(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1: data
outputs:
  wf_output_1:
    outputSource: input1
steps: []
""", test_data={"input1": "hello world"}, history_id=history_id)
            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            invocation_response = self._get("workflows/%s/invocations/%s" % (workflow_id, invocation_id))
            self._assert_status_code_is(invocation_response, 200)
            invocation = invocation_response.json()
            self._assert_has_keys(invocation , "id", "outputs", "output_collections")
            assert len(invocation["output_collections"]) == 0
            assert len(invocation["outputs"]) == 1
            output_content = self.dataset_populator.get_history_dataset_content(history_id, content_id=invocation["outputs"]["wf_output_1"]["id"])
            assert output_content == "hello world\n"

    @skip_without_tool("cat")
    def test_workflow_input_mapping(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1: data
outputs:
  wf_output_1:
    outputSource: first_cat/out_file1
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input1
""", test_data="""
input1:
  type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
    - identifier: el2
      value: 1.fastq
      type: File
""", history_id=history_id)
            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            invocation_response = self._get("workflows/%s/invocations/%s" % (workflow_id, invocation_id))
            self._assert_status_code_is(invocation_response, 200)
            invocation = invocation_response.json()
            self._assert_has_keys(invocation , "id", "outputs", "output_collections")
            assert len(invocation["output_collections"]) == 1
            assert len(invocation["outputs"]) == 0
            output_content = self.dataset_populator.get_history_collection_details(history_id, content_id=invocation["output_collections"]["wf_output_1"]["id"])
            self._assert_has_keys(output_content , "id", "elements")
            elements = output_content["elements"]
            assert len(elements) == 2
            elements0 = elements[0]
            assert elements0["element_identifier"] == "el1"

    @skip_without_tool("collection_creates_pair")
    def test_workflow_run_input_mapping_with_output_collections(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_jobs("""
class: GalaxyWorkflow
inputs:
  text_input: data
outputs:
  wf_output_1:
    outputSource: split_up/paired_output
steps:
  split_up:
    tool_id: collection_creates_pair
    in:
      input1: text_input
""", test_data="""
text_input:
  type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
    - identifier: el2
      value: 1.fastq
      type: File
""", history_id=history_id)
            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            invocation_response = self._get("workflows/%s/invocations/%s" % (workflow_id, invocation_id))
            self._assert_status_code_is(invocation_response, 200)
            invocation = invocation_response.json()
            self._assert_has_keys(invocation , "id", "outputs", "output_collections")
            assert len(invocation["output_collections"]) == 1
            assert len(invocation["outputs"]) == 0
            output_content = self.dataset_populator.get_history_collection_details(history_id, content_id=invocation["output_collections"]["wf_output_1"]["id"])
            self._assert_has_keys(output_content , "id", "elements")
            assert output_content["collection_type"] == "list:paired", output_content
            elements = output_content["elements"]
            assert len(elements) == 2
            elements0 = elements[0]
            assert elements0["element_identifier"] == "el1"

    def test_workflow_run_input_mapping_with_subworkflows(self):
        with self.dataset_populator.test_history() as history_id:
            test_data = """
outer_input:
  type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
    - identifier: el2
      value: 1.fastq
      type: File
"""
            summary = self._run_jobs(WORKFLOW_NESTED_SIMPLE, test_data=test_data, history_id=history_id)
            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            invocation_response = self._get("workflows/%s/invocations/%s" % (workflow_id, invocation_id))
            self._assert_status_code_is(invocation_response, 200)
            invocation_response = self._get("workflows/%s/invocations/%s" % (workflow_id, invocation_id))
            self._assert_status_code_is(invocation_response, 200)
            invocation = invocation_response.json()
            self._assert_has_keys(invocation , "id", "outputs", "output_collections")
            assert len(invocation["output_collections"]) == 1, invocation
            assert len(invocation["outputs"]) == 0
            output_content = self.dataset_populator.get_history_collection_details(history_id, content_id=invocation["output_collections"]["outer_output"]["id"])
            self._assert_has_keys(output_content , "id", "elements")
            assert output_content["collection_type"] == "list", output_content
            elements = output_content["elements"]
            assert len(elements) == 2
            elements0 = elements[0]
            assert elements0["element_identifier"] == "el1"

    @skip_without_tool("cat_list")
    @skip_without_tool("random_lines1")
    @skip_without_tool("split")
    def test_subworkflow_recover_mapping_1(self):
        # This test case tests an outer workflow continues to scheduling and handle
        # collection mapping properly after the last step of a subworkflow requires delayed
        # evaluation. Testing rescheduling and propagating connections within a subworkflow
        # is handled by the next test case.
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  outer_input: data
outputs:
  outer_output:
    outputSource: second_cat/out_file1
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: outer_input
  nested_workflow:
    run:
      class: GalaxyWorkflow
      inputs:
        inner_input: data
      outputs:
        workflow_output:
          outputSource: random_lines/out_file1
      steps:
        random_lines:
          tool_id: random_lines1
          state:
            num_lines: 2
            input:
              $link: inner_input
            seed_source:
              seed_source_selector: set_seed
              seed: asdf
    in:
      inner_input: first_cat/out_file1
  split:
    tool_id: split
    in:
      input1: nested_workflow/workflow_output
  second_cat:
    tool_id: cat_list
    in:
      input1: split/output

test_data:
  outer_input:
    value: 1.bed
    type: File
""", history_id=history_id, wait=True, round_trip_format_conversion=True)
            self.assertEqual("chr6\t108722976\t108723115\tCCDS5067.1_cds_0_0_chr6_108722977_f\t0\t+\nchrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\n", self.dataset_populator.get_history_dataset_content(history_id))
            # self.assertEqual("chr16\t142908\t143003\tCCDS10397.1_cds_0_0_chr16_142909_f\t0\t+\nchrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\n", self.dataset_populator.get_history_dataset_content(history_id))

    @skip_without_tool("cat_list")
    @skip_without_tool("random_lines1")
    @skip_without_tool("split")
    def test_subworkflow_recover_mapping_2(self):
        # Like the above test case, this test case tests an outer workflow continues to
        # schedule and handle collection mapping properly after a subworkflow needs to be
        # delayed, but this also tests recovering and handling scheduling within the subworkflow
        # since the delayed step (split) isn't the last step of the subworkflow.
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  outer_input: data
outputs:
  outer_output:
    outputSource: second_cat/out_file1
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: outer_input
  nested_workflow:
    run:
      class: GalaxyWorkflow
      inputs:
        inner_input: data
      outputs:
        workflow_output:
          outputSource: inner_cat/out_file1
      steps:
        random_lines:
          tool_id: random_lines1
          in:
            input: inner_input
            num_lines:
              default: 2
            seed_source|seed_source_selector:
              default: set_seed
            seed_source|seed:
              default: asdf
        split:
          tool_id: split
          in:
            input1: random_lines/out_file1
        inner_cat:
          tool_id: cat1
          in:
            input1: split/output
    in:
      inner_input: first_cat/out_file1
  second_cat:
    tool_id: cat_list
    in:
      input1: nested_workflow/workflow_output
""", test_data="""
outer_input:
  value: 1.bed
  type: File
""", history_id=history_id, wait=True, round_trip_format_conversion=True)
            self.assertEqual("chr6\t108722976\t108723115\tCCDS5067.1_cds_0_0_chr6_108722977_f\t0\t+\nchrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\n", self.dataset_populator.get_history_dataset_content(history_id))

    @skip_without_tool("cat_list")
    @skip_without_tool("random_lines1")
    @skip_without_tool("split")
    def test_recover_mapping_in_subworkflow(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  outer_input: data
outputs:
  outer_output:
    outputSource: second_cat/out_file1
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: outer_input
  nested_workflow:
    run:
      class: GalaxyWorkflow
      inputs:
        inner_input: data
      outputs:
        workflow_output:
          outputSource: split/output
      steps:
        random_lines:
          tool_id: random_lines1
          state:
            num_lines: 2
            input:
              $link: inner_input
            seed_source:
              seed_source_selector: set_seed
              seed: asdf
        split:
          tool_id: split
          in:
            input1: random_lines/out_file1
    in:
      inner_input: first_cat/out_file1
  second_cat:
    tool_id: cat_list
    in:
      input1: nested_workflow/workflow_output
""", test_data="""
outer_input:
  value: 1.bed
  type: File
""", history_id=history_id, wait=True, round_trip_format_conversion=True)
            self.assertEqual("chr6\t108722976\t108723115\tCCDS5067.1_cds_0_0_chr6_108722977_f\t0\t+\nchrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\n", self.dataset_populator.get_history_dataset_content(history_id))

    @skip_without_tool("empty_list")
    @skip_without_tool("count_list")
    @skip_without_tool("random_lines1")
    def test_empty_list_mapping(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1: data
outputs:
  count_list:
    outputSource: count_list/out_file1
steps:
  empty_list:
    tool_id: empty_list
    in:
      input1: input1
  random_lines:
    tool_id: random_lines1
    state:
      num_lines: 2
      input:
        $link: empty_list#output
      seed_source:
        seed_source_selector: set_seed
        seed: asdf
  count_list:
    tool_id: count_list
    in:
      input1: random_lines/out_file1
""", test_data="""
input1:
  value: 1.bed
  type: File
""", history_id=history_id, wait=True)
            self.assertEqual("0\n", self.dataset_populator.get_history_dataset_content(history_id))

    @skip_without_tool("collection_type_source_map_over")
    def test_mapping_and_subcollection_mapping(self):
        with self.dataset_populator.test_history() as history_id:
            jobs_summary = self._run_jobs("""
class: GalaxyWorkflow
inputs:
  text_input1: collection
steps:
  map_over:
    tool_id: collection_type_source_map_over
    in:
      input_collect: text_input1
""", test_data="""
text_input1:
  type: "list:paired"
""", history_id=history_id)
            hdca = self.dataset_populator.get_history_collection_details(history_id=jobs_summary.history_id, hid=1)
            assert hdca['collection_type'] == 'list:paired'
            assert len(hdca['elements'][0]['object']["elements"]) == 2

    @skip_without_tool("empty_list")
    @skip_without_tool("count_multi_file")
    @skip_without_tool("random_lines1")
    def test_empty_list_reduction(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1: data
outputs:
  count_multi_file:
    outputSource: count_multi_file/out_file1
steps:
  empty_list:
    tool_id: empty_list
    in:
      input1: input1
  random_lines:
    tool_id: random_lines1
    state:
      num_lines: 2
      input:
        $link: empty_list#output
      seed_source:
        seed_source_selector: set_seed
        seed: asdf
  count_multi_file:
    tool_id: count_multi_file
    in:
      input1: random_lines/out_file1
""", test_data="""
input1:
  value: 1.bed
  type: File
""", history_id=history_id, wait=True, round_trip_format_conversion=True)
            self.assertEqual("0\n", self.dataset_populator.get_history_dataset_content(history_id))

    @skip_without_tool("cat")
    def test_cancel_new_workflow_when_history_deleted(self):
        with self.dataset_populator.test_history() as history_id:
            # Invoke a workflow with a pause step.
            uploaded_workflow_id, invocation_id = self._invoke_paused_workflow(history_id)

            # There is no pause of anything in here, so likely the invocation is
            # is still in a new state. If it isn't that is fine, continue with the
            # test it will just happen to test the same thing as below.

            # Wait for all the datasets to complete, make sure the workflow invocation
            # is not complete.
            self._assert_invocation_non_terminal(uploaded_workflow_id, invocation_id)

            self._delete("histories/%s" % history_id)

            invocation_cancelled = self._wait_for_invocation_state(uploaded_workflow_id, invocation_id, 'cancelled')
            assert invocation_cancelled, "Workflow state is not cancelled..."

    @skip_without_tool("cat")
    def test_cancel_ready_workflow_when_history_deleted(self):
        # Same as previous test but make sure invocation isn't a new state before
        # cancelling.
        with self.dataset_populator.test_history() as history_id:
            # Invoke a workflow with a pause step.
            uploaded_workflow_id, invocation_id = self._invoke_paused_workflow(history_id)

            # Wait for at least one scheduling step.
            self._wait_for_invocation_non_new(uploaded_workflow_id, invocation_id)

            # Wait for all the datasets to complete, make sure the workflow invocation
            # is not complete.
            self._assert_invocation_non_terminal(uploaded_workflow_id, invocation_id)

            self._delete("histories/%s" % history_id)

            invocation_cancelled = self._wait_for_invocation_state(uploaded_workflow_id, invocation_id, 'cancelled')
            assert invocation_cancelled, "Workflow state is not cancelled..."

    @skip_without_tool("cat")
    def test_workflow_pause(self):
        with self.dataset_populator.test_history() as history_id:
            # Invoke a workflow with a pause step.
            uploaded_workflow_id, invocation_id = self._invoke_paused_workflow(history_id)

            # Wait for at least one scheduling step.
            self._wait_for_invocation_non_new(uploaded_workflow_id, invocation_id)

            # Make sure the history didn't enter a failed state in there.
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            # Assert the workflow hasn't finished scheduling, we can be pretty sure we
            # are at the pause step in this case then.
            self._assert_invocation_non_terminal(uploaded_workflow_id, invocation_id)

            # Review the paused steps to allow the workflow to continue.
            self.__review_paused_steps(uploaded_workflow_id, invocation_id, order_index=2, action=True)

            # Wait for the workflow to finish scheduling and ensure both the invocation
            # and the history are in valid states.
            invocation_scheduled = self._wait_for_invocation_state(uploaded_workflow_id, invocation_id, 'scheduled')
            assert invocation_scheduled, "Workflow state is not scheduled..."
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

    @skip_without_tool("cat")
    def test_workflow_pause_cancel(self):
        with self.dataset_populator.test_history() as history_id:
            # Invoke a workflow with a pause step.
            uploaded_workflow_id, invocation_id = self._invoke_paused_workflow(history_id)

            # Wait for at least one scheduling step.
            self._wait_for_invocation_non_new(uploaded_workflow_id, invocation_id)

            # Make sure the history didn't enter a failed state in there.
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            # Assert the workflow hasn't finished scheduling, we can be pretty sure we
            # are at the pause step in this case then.
            self._assert_invocation_non_terminal(uploaded_workflow_id, invocation_id)

            # Review the paused workflow and cancel it at the paused step.
            self.__review_paused_steps(uploaded_workflow_id, invocation_id, order_index=2, action=False)

            # Ensure the workflow eventually becomes cancelled.
            invocation_cancelled = self._wait_for_invocation_state(uploaded_workflow_id, invocation_id, 'cancelled')
            assert invocation_cancelled, "Workflow state is not cancelled..."

    @skip_without_tool("head")
    def test_workflow_map_reduce_pause(self):
        with self.dataset_populator.test_history() as history_id:
            workflow = self.workflow_populator.load_workflow_from_resource("test_workflow_map_reduce_pause")
            uploaded_workflow_id = self.workflow_populator.create_workflow(workflow)
            hda1 = self.dataset_populator.new_dataset(history_id, content="reviewed\nunreviewed")
            hdca1 = self.dataset_collection_populator.create_list_in_history(history_id, contents=["1\n2\n3", "4\n5\n6"]).json()
            index_map = {
                '0': self._ds_entry(hda1),
                '1': self._ds_entry(hdca1),
            }
            invocation_id = self.__invoke_workflow(history_id, uploaded_workflow_id, index_map)

            # Wait for at least one scheduling step.
            self._wait_for_invocation_non_new(uploaded_workflow_id, invocation_id)

            # Make sure the history didn't enter a failed state in there.
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            # Assert the workflow hasn't finished scheduling, we can be pretty sure we
            # are at the pause step in this case then.
            self._assert_invocation_non_terminal(uploaded_workflow_id, invocation_id)

            self.__review_paused_steps(uploaded_workflow_id, invocation_id, order_index=4, action=True)
            self.wait_for_invocation_and_jobs(history_id, uploaded_workflow_id, invocation_id)
            invocation = self._invocation_details(uploaded_workflow_id, invocation_id)
            assert invocation['state'] == 'scheduled'
            self.assertEqual("reviewed\n1\nreviewed\n4\n", self.dataset_populator.get_history_dataset_content(history_id))

    @skip_without_tool("cat")
    def test_cancel_workflow_invocation(self):
        with self.dataset_populator.test_history() as history_id:
            # Invoke a workflow with a pause step.
            uploaded_workflow_id, invocation_id = self._invoke_paused_workflow(history_id)

            # Wait for at least one scheduling step.
            self._wait_for_invocation_non_new(uploaded_workflow_id, invocation_id)

            # Make sure the history didn't enter a failed state in there.
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            # Assert the workflow hasn't finished scheduling, we can be pretty sure we
            # are at the pause step in this case then.
            self._assert_invocation_non_terminal(uploaded_workflow_id, invocation_id)

            invocation_url = self._api_url("workflows/%s/usage/%s" % (uploaded_workflow_id, invocation_id), use_key=True)
            delete_response = delete(invocation_url)
            self._assert_status_code_is(delete_response, 200)

            invocation = self._invocation_details(uploaded_workflow_id, invocation_id)
            assert invocation['state'] == 'cancelled'

    @skip_without_tool("cat")
    def test_pause_outputs_with_deleted_inputs(self):
        # We run a workflow on a collection with a deleted element.
        with self.dataset_populator.test_history() as history_id:
            workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
inputs:
  input1:
    type: collection
    collection_type: list
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input1
  second_cat:
    tool_id: cat
    in:
      input1: first_cat/out_file1
""")
            DELETED = 0
            PAUSED_1 = 3
            PAUSED_2 = 5
            hdca1 = self.dataset_collection_populator.create_list_in_history(history_id,
                                                                             contents=[("sample1-1", "1 2 3")]).json()
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            r = self._delete("histories/%s/contents/%s" % (history_id, hdca1['elements'][DELETED]['object']['id']))
            label_map = {"input1": self._ds_entry(hdca1)}
            workflow_request = dict(
                history="hist_id=%s" % history_id,
                workflow_id=workflow_id,
                ds_map=self._build_ds_map(workflow_id, label_map),
            )
            r = self._post("workflows", data=workflow_request)
            self._assert_status_code_is(r, 200)
            # If this starts failing we may have prevented running workflows on collections with deleted members,
            # in which case we can disable this test.
            self.dataset_populator.wait_for_history_jobs(history_id, assert_ok=False)
            contents = self.__history_contents(history_id)
            assert contents[DELETED]['deleted']
            assert contents[PAUSED_1]['state'] == 'paused'
            assert contents[PAUSED_2]['state'] == 'paused'

    def test_run_with_implicit_connection(self):
        with self.dataset_populator.test_history() as history_id:
            run_summary = self._run_jobs("""
class: GalaxyWorkflow
inputs:
  test_input: data
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: test_input
  the_pause:
    type: pause
    in:
      input: first_cat/out_file1
  second_cat:
    tool_id: cat1
    in:
      input1: the_pause
  third_cat:
    tool_id: random_lines1
    in:
      $step: second_cat
    state:
      num_lines: 1
      input:
        $link: test_input
      seed_source:
        seed_source_selector: set_seed
        seed: asdf
""", test_data={"test_input": "hello world"}, history_id=history_id, wait=False, round_trip_format_conversion=True)
            history_id = run_summary.history_id
            workflow_id = run_summary.workflow_id
            invocation_id = run_summary.invocation_id
            # Wait for first two jobs to be scheduled - upload and first cat.
            wait_on(lambda: len(self._history_jobs(history_id)) >= 2 or None, "history jobs")
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            invocation = self._invocation_details(workflow_id, invocation_id)
            assert invocation['state'] != 'scheduled', invocation
            # Expect two jobs - the upload and first cat. randomlines shouldn't run
            # it is implicitly dependent on second cat.
            self._assert_history_job_count(history_id, 2)

            self.__review_paused_steps(workflow_id, invocation_id, order_index=2, action=True)
            self.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)
            self._assert_history_job_count(history_id, 4)

    def test_run_with_validated_parameter_connection_valid(self):
        with self.dataset_populator.test_history() as history_id:
            run_summary = self._run_jobs("""
class: GalaxyWorkflow
inputs:
  text_input: text
steps:
  validation:
    tool_id: validation_repeat
    state:
      r2:
      - text:
          $link: text_input
""", test_data="""
text_input:
  value: "abd"
  type: raw
""", history_id=history_id, wait=True, round_trip_format_conversion=True)
            self.wait_for_invocation_and_jobs(history_id, run_summary.workflow_id, run_summary.invocation_id)
            jobs = self._history_jobs(history_id)
            assert len(jobs) == 1

    def test_run_with_validated_parameter_connection_invalid(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  text_input: text
steps:
  validation:
    tool_id: validation_repeat
    state:
      r2:
      - text:
          $link: text_input
""", test_data="""
text_input:
  value: ""
  type: raw
""", history_id=history_id, wait=True, assert_ok=False)

    def test_run_with_text_connection(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  data_input: data
  text_input: text
steps:
  randomlines:
    tool_id: random_lines1
    state:
      num_lines: 1
      input:
        $link: data_input
      seed_source:
        seed_source_selector: set_seed
        seed:
          $link: text_input
""", test_data="""
data_input:
  value: 1.bed
  type: File
text_input:
  value: asdf
  type: raw
""", history_id=history_id)

            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            content = self.dataset_populator.get_history_dataset_content(history_id)
            self.assertEqual("chrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\n", content)

    @skip_without_tool('cat1')
    def test_workflow_rerun_with_use_cached_job(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_run")
        # We launch a workflow
        with self.dataset_populator.test_history() as history_id_one, self.dataset_populator.test_history() as history_id_two:
            workflow_request, _ = self._setup_workflow_run(workflow, history_id=history_id_one)
            run_workflow_response = self._post("workflows", data=workflow_request).json()
            # We copy the workflow inputs to a new history
            new_workflow_request = workflow_request.copy()
            new_ds_map = json.loads(new_workflow_request['ds_map'])
            for key, input_values in run_workflow_response['inputs'].items():
                copy_payload = {"content": input_values['id'], "source": "hda", "type": "dataset"}
                copy_response = self._post("histories/%s/contents" % history_id_two, data=copy_payload).json()
                new_ds_map[key]['id'] = copy_response['id']
            new_workflow_request['ds_map'] = json.dumps(new_ds_map, sort_keys=True)
            new_workflow_request['history'] = "hist_id=%s" % history_id_two
            new_workflow_request['use_cached_job'] = True
            # We run the workflow again, it should not produce any new outputs
            new_workflow_response = self._post("workflows", data=new_workflow_request).json()
            first_wf_output = self._get("datasets/%s" % run_workflow_response['outputs'][0]).json()
            second_wf_output = self._get("datasets/%s" % new_workflow_response['outputs'][0]).json()
            assert first_wf_output['file_name'] == second_wf_output['file_name'], \
                "first output:\n%s\nsecond output:\n%s" % (first_wf_output, second_wf_output)

    @skip_without_tool('cat1')
    def test_nested_workflow_rerun_with_use_cached_job(self):
        with self.dataset_populator.test_history() as history_id_one, self.dataset_populator.test_history() as history_id_two:
            test_data = """
outer_input:
  value: 1.bed
  type: File
"""
            run_jobs_summary = self._run_jobs(WORKFLOW_NESTED_SIMPLE, test_data=test_data, history_id=history_id_one)
            workflow_request = run_jobs_summary.workflow_request
            # We copy the inputs to a new history and re-run the workflow
            inputs = json.loads(workflow_request['inputs'])
            dataset_type = inputs['outer_input']['src']
            dataset_id = inputs['outer_input']['id']
            copy_payload = {"content": dataset_id, "source": dataset_type, "type": "dataset"}
            copy_response = self._post("histories/%s/contents" % history_id_two, data=copy_payload)
            self._assert_status_code_is(copy_response, 200)
            new_dataset_id = copy_response.json()['id']
            inputs['outer_input']['id'] = new_dataset_id
            workflow_request['use_cached_job'] = True
            workflow_request['history'] = "hist_id={history_id_two}".format(history_id_two=history_id_two)
            workflow_request['inputs'] = json.dumps(inputs)
            run_workflow_response = self._post("workflows", data=run_jobs_summary.workflow_request).json()
            self.workflow_populator.wait_for_workflow(workflow_request['workflow_id'],
                                                      run_workflow_response['id'],
                                                      history_id_two,
                                                      assert_ok=True)
            # Now make sure that the HDAs in each history point to the same dataset instances
            history_one_contents = self.__history_contents(history_id_one)
            history_two_contents = self.__history_contents(history_id_two)
            assert len(history_one_contents) == len(history_two_contents)
            for i, (item_one, item_two) in enumerate(zip(history_one_contents, history_two_contents)):
                assert item_one['dataset_id'] == item_two['dataset_id'], \
                    'Dataset ids should match, but "%s" and "%s" are not the same for History item %i.' % (item_one['dataset_id'],
                                                                                                           item_two['dataset_id'],
                                                                                                           i + 1)

    def test_cannot_run_inaccessible_workflow(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_run_cannot_access")
        workflow_request, history_id = self._setup_workflow_run(workflow)
        with self._different_user():
            run_workflow_response = self._post("workflows", data=workflow_request)
            self._assert_status_code_is(run_workflow_response, 403)

    def test_400_on_invalid_workflow_id(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_run_does_not_exist")
        workflow_request, history_id = self._setup_workflow_run(workflow)
        workflow_request["workflow_id"] = self._random_key()
        run_workflow_response = self._post("workflows", data=workflow_request)
        self._assert_status_code_is(run_workflow_response, 400)

    def test_cannot_run_against_other_users_history(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_run_does_not_exist")
        workflow_request, history_id = self._setup_workflow_run(workflow)
        with self._different_user():
            other_history_id = self.dataset_populator.new_history()
        workflow_request["history"] = "hist_id=%s" % other_history_id
        run_workflow_response = self._post("workflows", data=workflow_request)
        self._assert_status_code_is(run_workflow_response, 403)

    @skip_without_tool("cat")
    @skip_without_tool("cat_list")
    def test_workflow_run_with_matching_lists(self):
        workflow = self.workflow_populator.load_workflow_from_resource("test_workflow_matching_lists")
        workflow_id = self.workflow_populator.create_workflow(workflow)
        with self.dataset_populator.test_history() as history_id:
            hdca1 = self.dataset_collection_populator.create_list_in_history(history_id, contents=[("sample1-1", "1 2 3"), ("sample2-1", "7 8 9")]).json()
            hdca2 = self.dataset_collection_populator.create_list_in_history(history_id, contents=[("sample1-2", "4 5 6"), ("sample2-2", "0 a b")]).json()
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            label_map = {"list1": self._ds_entry(hdca1), "list2": self._ds_entry(hdca2)}
            workflow_request = dict(
                history="hist_id=%s" % history_id,
                workflow_id=workflow_id,
                ds_map=self._build_ds_map(workflow_id, label_map),
            )
            run_workflow_response = self._post("workflows", data=workflow_request)
            self._assert_status_code_is(run_workflow_response, 200)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            self.assertEqual("1 2 3\n4 5 6\n7 8 9\n0 a b\n", self.dataset_populator.get_history_dataset_content(history_id))

    def test_workflow_stability(self):
        # Run this index stability test with following command:
        #   ./run_tests.sh test/api/test_workflows.py:WorkflowsApiTestCase.test_workflow_stability
        num_tests = 1
        for workflow_file in ["test_workflow_topoambigouity", "test_workflow_topoambigouity_auto_laidout"]:
            workflow = self.workflow_populator.load_workflow_from_resource(workflow_file)
            last_step_map = self._step_map(workflow)
            for i in range(num_tests):
                uploaded_workflow_id = self.workflow_populator.create_workflow(workflow)
                downloaded_workflow = self._download_workflow(uploaded_workflow_id)
                step_map = self._step_map(downloaded_workflow)
                assert step_map == last_step_map
                last_step_map = step_map

    def _step_map(self, workflow):
        # Build dict mapping 'tep index to input name.
        step_map = {}
        for step_index, step in workflow["steps"].items():
            if step["type"] == "data_input":
                step_map[step_index] = step["inputs"][0]["name"]
        return step_map

    def test_empty_create(self):
        response = self._post("workflows")
        self._assert_status_code_is(response, 400)
        self._assert_error_code_is(response, error_codes.USER_REQUEST_MISSING_PARAMETER)

    def test_invalid_create_multiple_types(self):
        data = {
            'shared_workflow_id': '1234567890abcdef',
            'from_history_id': '1234567890abcdef'
        }
        response = self._post("workflows", data)
        self._assert_status_code_is(response, 400)
        self._assert_error_code_is(response, error_codes.USER_REQUEST_INVALID_PARAMETER)

    @skip_without_tool("cat1")
    def test_run_with_pja(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_pja_run", add_pja=True)
        workflow_request, history_id = self._setup_workflow_run(workflow, inputs_by='step_index')
        workflow_request["replacement_params"] = dumps(dict(replaceme="was replaced"))
        run_workflow_response = self._post("workflows", data=workflow_request)
        self._assert_status_code_is(run_workflow_response, 200)
        content = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=True)
        assert content["name"] == "foo was replaced"

    @skip_without_tool("output_filter")
    def test_optional_workflow_output(self):
        with self.dataset_populator.test_history() as history_id:
            run_object = self._run_jobs("""
class: GalaxyWorkflow
inputs: []
outputs:
  wf_output_1:
    outputSource: output_filter/out_1
steps:
  output_filter:
    tool_id: output_filter
    state:
      produce_out_1: False
      filter_text_1: '1'
      produce_collection: False
""", test_data={}, history_id=history_id, wait=False)
            self.wait_for_invocation_and_jobs(history_id, run_object.workflow_id, run_object.invocation_id)
            contents = self.__history_contents(history_id)
            assert len(contents) == 1
            okay_dataset = contents[0]
            assert okay_dataset["state"] == "ok"

    @skip_without_tool("cat")
    def test_run_rename_on_mapped_over_collection(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1:
    type: collection
    collection_type: list
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input1
    outputs:
      out_file1:
        rename: "my new name"
""", test_data="""
input1:
  type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
""", history_id=history_id)
            content = self.dataset_populator.get_history_dataset_details(history_id, hid=4, wait=True, assert_ok=True)
            name = content["name"]
            assert name == "my new name", name
            assert content["history_content_type"] == "dataset"
            content = self.dataset_populator.get_history_collection_details(history_id, hid=3, wait=True, assert_ok=True)
            name = content["name"]
            assert content["history_content_type"] == "dataset_collection", content
            assert name == "my new name", name

    @skip_without_tool("cat")
    def test_run_rename_based_on_inputs_on_mapped_over_collection(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1:
    type: collection
    collection_type: list
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input1
    outputs:
      out_file1:
        rename: "#{input1} suffix"
""", test_data="""
input1:
  type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
""", history_id=history_id)
            content = self.dataset_populator.get_history_collection_details(history_id, hid=3, wait=True, assert_ok=True)
            name = content["name"]
            assert content["history_content_type"] == "dataset_collection", content
            assert name == "the_dataset_list suffix", name

    @skip_without_tool("collection_creates_pair")
    def test_run_rename_collection_output(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  - tool_id: collection_creates_pair
    in:
      input1: input1
    outputs:
      paired_output:
        rename: "my new name"
""", test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
""", history_id=history_id)
            details1 = self.dataset_populator.get_history_collection_details(history_id, hid=4, wait=True, assert_ok=True)

            assert details1["name"] == "my new name", details1
            assert details1["history_content_type"] == "dataset_collection"

    @skip_without_tool("create_2")
    def test_run_rename_multiple_outputs(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs: []
steps:
  create_2:
    tool_id: create_2
    state:
      sleep_time: 0
    outputs:
      out_file1:
        rename: "my new name"
      out_file2:
        rename: "my other new name"
""", test_data={}, history_id=history_id)
        details1 = self.dataset_populator.get_history_dataset_details(history_id, hid=1, wait=True, assert_ok=True)
        details2 = self.dataset_populator.get_history_dataset_details(history_id, hid=2)

        assert details1["name"] == "my new name"
        assert details2["name"] == "my other new name"

    @skip_without_tool("cat")
    def test_run_rename_based_on_input(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(WORKFLOW_RENAME_ON_INPUT, history_id=history_id)
            content = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=True)
            name = content["name"]
            assert name == "fasta1 suffix", name

    @skip_without_tool("fail_identifier")
    @skip_without_tool("cat")
    def test_run_rename_when_resuming_jobs(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  first_fail:
    tool_id: fail_identifier
    state:
      failbool: true
      input1:
        $link: input1
    outputs:
      out_file1:
        rename: "cat1 out"
  cat:
    tool_id: cat
    in:
      input1: first_fail/out_file1
    outputs:
      out_file1:
        rename: "#{input1} suffix"
""", test_data="""
input1:
  value: 1.fasta
  type: File
  name: fail
""", history_id=history_id, wait=True, assert_ok=False)
            content = self.dataset_populator.get_history_dataset_details(history_id, hid=2, wait=True, assert_ok=False)
            name = content["name"]
            assert content['state'] == 'error', content
            input1 = self.dataset_populator.get_history_dataset_details(history_id, hid=1, wait=True, assert_ok=False)
            job_id = content['creating_job']
            inputs = {"input1": {'values': [{'src': 'hda',
                                             'id': input1['id']}]
                                 },
                      "failbool": "false",
                      "rerun_remap_job_id": job_id}
            self.dataset_populator.run_tool(tool_id='fail_identifier',
                                            inputs=inputs,
                                            history_id=history_id,
                                            assert_ok=True)
            unpaused_dataset = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=False)
            assert unpaused_dataset['state'] == 'ok'
            assert unpaused_dataset['name'] == "%s suffix" % name

    @skip_without_tool("cat")
    def test_run_rename_based_on_input_recursive(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input1
    outputs:
      out_file1:
        rename: "#{input1} #{input1 | upper} suffix"
""", test_data="""
input1:
  value: 1.fasta
  type: File
  name: '#{input1}'
""", history_id=history_id)
            content = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=True)
            name = content["name"]
            assert name == "#{input1} #{INPUT1} suffix", name

    @skip_without_tool("cat")
    def test_run_rename_based_on_input_repeat(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1: data
  input2: data
steps:
  first_cat:
    tool_id: cat
    state:
      input1:
        $link: input1
      queries:
        - input2:
            $link: input2
    outputs:
      out_file1:
        rename: "#{queries_0.input2| basename} suffix"
""", test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
input2:
  value: 1.fasta
  type: File
  name: fasta2
""", history_id=history_id)
            content = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=True)
            name = content["name"]
            assert name == "fasta2 suffix", name

    @skip_without_tool("mapper2")
    def test_run_rename_based_on_input_conditional(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  fasta_input: data
  fastq_input: data
steps:
  mapping:
    tool_id: mapper2
    state:
      fastq_input:
        fastq_input_selector: single
        fastq_input1:
          $link: fastq_input
      reference:
        $link: fasta_input
    outputs:
      out_file1:
        # Wish it was qualified for conditionals but it doesn't seem to be. -John
        # rename: "#{fastq_input.fastq_input1 | basename} suffix"
        rename: "#{fastq_input1 | basename} suffix"
""", test_data="""
fasta_input:
  value: 1.fasta
  type: File
  name: fasta1
  file_type: fasta
fastq_input:
  value: 1.fastqsanger
  type: File
  name: fastq1
  file_type: fastqsanger
""", history_id=history_id)
            content = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=True)
            name = content["name"]
            assert name == "fastq1 suffix", name

    @skip_without_tool("mapper2")
    def test_run_rename_based_on_input_collection(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  fasta_input: data
  fastq_inputs: data
steps:
  mapping:
    tool_id: mapper2
    state:
      fastq_input:
        fastq_input_selector: paired_collection
        fastq_input1:
          $link: fastq_inputs
      reference:
        $link: fasta_input
    outputs:
      out_file1:
        # Wish it was qualified for conditionals but it doesn't seem to be. -John
        # rename: "#{fastq_input.fastq_input1 | basename} suffix"
        rename: "#{fastq_input1} suffix"
""", test_data="""
fasta_input:
  value: 1.fasta
  type: File
  name: fasta1
  file_type: fasta
fastq_inputs:
  type: list
  name: the_dataset_pair
  elements:
    - identifier: forward
      value: 1.fastq
      type: File
    - identifier: reverse
      value: 1.fastq
      type: File
""", history_id=history_id)
            content = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=True)
            name = content["name"]
            assert name == "the_dataset_pair suffix", name

    @skip_without_tool("collection_creates_pair")
    def test_run_hide_on_collection_output(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  create_pair:
    tool_id: collection_creates_pair
    state:
      input1:
        $link: input1
    outputs:
      paired_output:
        hide: true
""", test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
""", history_id=history_id)
            details1 = self.dataset_populator.get_history_collection_details(history_id, hid=4, wait=True, assert_ok=True)

            assert details1["history_content_type"] == "dataset_collection"
            assert not details1["visible"], details1

    @skip_without_tool("cat")
    def test_run_hide_on_mapped_over_collection(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  - id: input1
    type: data_collection_input
    collection_type: list
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input1
    outputs:
      out_file1:
        hide: true
""", test_data="""
input1:
  type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
""", history_id=history_id)

            content = self.dataset_populator.get_history_dataset_details(history_id, hid=4, wait=True, assert_ok=True)
            assert content["history_content_type"] == "dataset"
            assert not content["visible"]

            content = self.dataset_populator.get_history_collection_details(history_id, hid=3, wait=True, assert_ok=True)
            assert content["history_content_type"] == "dataset_collection", content
            assert not content["visible"]

    @skip_without_tool("cat")
    def test_tag_auto_propagation(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input1
    outputs:
      out_file1:
        add_tags:
            - "name:treated1fb"
            - "group:condition:treated"
            - "group:type:single-read"
            - "machine:illumina"
  second_cat:
    tool_id: cat
    in:
      input1: first_cat/out_file1
""", test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
""", history_id=history_id, round_trip_format_conversion=True)

            details0 = self.dataset_populator.get_history_dataset_details(history_id, hid=2, wait=True, assert_ok=True)
            tags = details0["tags"]
            assert len(tags) == 4, details0
            assert "name:treated1fb" in tags, tags
            assert "group:condition:treated" in tags, tags
            assert "group:type:single-read" in tags, tags
            assert "machine:illumina" in tags, tags

            details1 = self.dataset_populator.get_history_dataset_details(history_id, hid=3, wait=True, assert_ok=True)
            tags = details1["tags"]
            assert len(tags) == 1, details1
            assert "name:treated1fb" in tags, tags

    @skip_without_tool("collection_creates_pair")
    def test_run_add_tag_on_collection_output(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  create_pair:
    tool_id: collection_creates_pair
    in:
      input1: input1
    outputs:
      paired_output:
        add_tags:
            - "name:foo"
""", test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
""", history_id=history_id, round_trip_format_conversion=True)
            details1 = self.dataset_populator.get_history_collection_details(history_id, hid=4, wait=True, assert_ok=True)

            assert details1["history_content_type"] == "dataset_collection"
            assert details1["tags"][0] == "name:foo", details1

    @skip_without_tool("cat")
    def test_run_add_tag_on_mapped_over_collection(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1:
    type: collection
    collection_type: list
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input1
    outputs:
      out_file1:
        add_tags:
            - "name:foo"
""", test_data="""
input1:
  type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
""", history_id=history_id, round_trip_format_conversion=True)
            details1 = self.dataset_populator.get_history_collection_details(history_id, hid=3, wait=True, assert_ok=True)

            assert details1["history_content_type"] == "dataset_collection"
            assert details1["tags"][0] == "name:foo", details1

    @skip_without_tool("collection_creates_pair")
    @skip_without_tool("cat")
    def test_run_remove_tag_on_collection_output(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input1
    outputs:
      out_file1:
        add_tags:
          - "name:foo"
  create_pair:
    tool_id: collection_creates_pair
    in:
      input1: first_cat#out_file1
    outputs:
      paired_output:
        remove_tags:
          - "name:foo"
""", test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
""", history_id=history_id, round_trip_format_conversion=True)
            details_dataset_with_tag = self.dataset_populator.get_history_dataset_details(history_id, hid=2, wait=True, assert_ok=True)

            assert details_dataset_with_tag["history_content_type"] == "dataset", details_dataset_with_tag
            assert details_dataset_with_tag["tags"][0] == "name:foo", details_dataset_with_tag

            details_collection_without_tag = self.dataset_populator.get_history_collection_details(history_id, hid=5, wait=True, assert_ok=True)
            assert details_collection_without_tag["history_content_type"] == "dataset_collection", details_collection_without_tag
            assert len(details_collection_without_tag["tags"]) == 0, details_collection_without_tag

    @skip_without_tool("cat1")
    def test_run_with_runtime_pja(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_pja_runtime")
        uuid0, uuid1, uuid2 = str(uuid4()), str(uuid4()), str(uuid4())
        workflow["steps"]["0"]["uuid"] = uuid0
        workflow["steps"]["1"]["uuid"] = uuid1
        workflow["steps"]["2"]["uuid"] = uuid2
        workflow_request, history_id = self._setup_workflow_run(workflow, inputs_by='step_index')
        workflow_request["replacement_params"] = dumps(dict(replaceme="was replaced"))

        pja_map = {
            "RenameDatasetActionout_file1": dict(
                action_type="RenameDatasetAction",
                output_name="out_file1",
                action_arguments=dict(newname="foo ${replaceme}"),
            )
        }
        workflow_request["parameters"] = dumps({
            uuid2: {"__POST_JOB_ACTIONS__": pja_map}
        })

        run_workflow_response = self._post("workflows", data=workflow_request)
        self._assert_status_code_is(run_workflow_response, 200)
        content = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=True)
        assert content["name"] == "foo was replaced", content["name"]

        # Test for regression of previous behavior where runtime post job actions
        # would be added to the original workflow post job actions.
        workflow_id = workflow_request["workflow_id"]
        downloaded_workflow = self._download_workflow(workflow_id)
        pjas = list(downloaded_workflow["steps"]["2"]["post_job_actions"].values())
        assert len(pjas) == 0, len(pjas)

    @skip_without_tool("cat1")
    def test_run_with_delayed_runtime_pja(self):
        workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
inputs:
  test_input: data
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: test_input
  the_pause:
    type: pause
    in:
      input: first_cat/out_file1
  second_cat:
    tool_id: cat1
    in:
      input1: the_pause
""", round_trip_format_conversion=True)
        downloaded_workflow = self._download_workflow(workflow_id)
        uuid_dict = dict((int(index), step["uuid"]) for index, step in downloaded_workflow["steps"].items())
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="1 2 3")
            self.dataset_populator.wait_for_history(history_id)
            inputs = {
                '0': self._ds_entry(hda),
            }
            uuid2 = uuid_dict[3]
            workflow_request = {}
            workflow_request["replacement_params"] = dumps(dict(replaceme="was replaced"))
            pja_map = {
                "RenameDatasetActionout_file1": dict(
                    action_type="RenameDatasetAction",
                    output_name="out_file1",
                    action_arguments=dict(newname="foo ${replaceme}"),
                )
            }
            workflow_request["parameters"] = dumps({
                uuid2: {"__POST_JOB_ACTIONS__": pja_map}
            })
            invocation_id = self.__invoke_workflow(history_id, workflow_id, inputs=inputs, request=workflow_request)

            time.sleep(2)
            self.dataset_populator.wait_for_history(history_id)
            self.__review_paused_steps(workflow_id, invocation_id, order_index=2, action=True)

            self.workflow_populator.wait_for_workflow(workflow_id, invocation_id, history_id)
            time.sleep(1)
            content = self.dataset_populator.get_history_dataset_details(history_id)
            assert content["name"] == "foo was replaced", content["name"]

    @skip_without_tool("cat1")
    def test_delete_intermediate_datasets_pja_1(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input1: data
outputs:
  wf_output_1:
    outputSource: third_cat/out_file1
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: input1
  second_cat:
    tool_id: cat1
    in:
      input1: first_cat/out_file1
  third_cat:
    tool_id: cat1
    in:
      input1: second_cat/out_file1
    outputs:
      out_file1:
        delete_intermediate_datasets: true
""", test_data={"input1": "hello world"}, history_id=history_id)
            hda1 = self.dataset_populator.get_history_dataset_details(history_id, hid=1)
            hda2 = self.dataset_populator.get_history_dataset_details(history_id, hid=2)
            hda3 = self.dataset_populator.get_history_dataset_details(history_id, hid=3)
            hda4 = self.dataset_populator.get_history_dataset_details(history_id, hid=4)
            assert not hda1["deleted"]
            assert hda2["deleted"]
            # I think hda3 should be deleted, but the inputs to
            # steps with workflow outputs are not deleted.
            # assert hda3["deleted"]
            print(hda3["deleted"])
            assert not hda4["deleted"]

    @skip_without_tool("random_lines1")
    def test_run_replace_params_by_tool(self):
        workflow_request, history_id = self._setup_random_x2_workflow("test_for_replace_tool_params")
        workflow_request["parameters"] = dumps(dict(random_lines1=dict(num_lines=5)))
        run_workflow_response = self._post("workflows", data=workflow_request)
        self._assert_status_code_is(run_workflow_response, 200)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        # Would be 8 and 6 without modification
        self.__assert_lines_hid_line_count_is(history_id, 2, 5)
        self.__assert_lines_hid_line_count_is(history_id, 3, 5)

    @skip_without_tool("random_lines1")
    def test_run_replace_params_by_uuid(self):
        workflow_request, history_id = self._setup_random_x2_workflow("test_for_replace_tool_params")
        workflow_request["parameters"] = dumps({
            "58dffcc9-bcb7-4117-a0e1-61513524b3b1": dict(num_lines=4),
            "58dffcc9-bcb7-4117-a0e1-61513524b3b2": dict(num_lines=3),
        })
        run_workflow_response = self._post("workflows", data=workflow_request)
        self._assert_status_code_is(run_workflow_response, 200)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        # Would be 8 and 6 without modification
        self.__assert_lines_hid_line_count_is(history_id, 2, 4)
        self.__assert_lines_hid_line_count_is(history_id, 3, 3)

    @skip_without_tool("cat1")
    @skip_without_tool("addValue")
    def test_run_batch(self):
        workflow = self.workflow_populator.load_workflow_from_resource("test_workflow_batch")
        workflow_id = self.workflow_populator.create_workflow(workflow)
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
            hda2 = self.dataset_populator.new_dataset(history_id, content="4 5 6")
            hda3 = self.dataset_populator.new_dataset(history_id, content="7 8 9")
            hda4 = self.dataset_populator.new_dataset(history_id, content="10 11 12")
            parameters = {
                "0": {"input": {"batch": True, "values": [{"id" : hda1.get("id"), "hid": hda1.get("hid"), "src": "hda"},
                                                          {"id" : hda2.get("id"), "hid": hda2.get("hid"), "src": "hda"},
                                                          {"id" : hda3.get("id"), "hid": hda2.get("hid"), "src": "hda"},
                                                          {"id" : hda4.get("id"), "hid": hda2.get("hid"), "src": "hda"}]}},
                "1": {"input": {"batch": False, "values": [{"id" : hda1.get("id"), "hid": hda1.get("hid"), "src": "hda"}]}, "exp": "2"}}
            workflow_request = {
                "history_id" : history_id,
                "batch"      : True,
                "parameters_normalized": True,
                "parameters" : dumps(parameters),
            }
            invocation_response = self._post("workflows/%s/usage" % workflow_id, data=workflow_request)
            self._assert_status_code_is(invocation_response, 200)
            time.sleep(5)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            r1 = "1 2 3\t1\n1 2 3\t2\n"
            r2 = "4 5 6\t1\n1 2 3\t2\n"
            r3 = "7 8 9\t1\n1 2 3\t2\n"
            r4 = "10 11 12\t1\n1 2 3\t2\n"
            t1 = self.dataset_populator.get_history_dataset_content(history_id, hid=7)
            t2 = self.dataset_populator.get_history_dataset_content(history_id, hid=10)
            t3 = self.dataset_populator.get_history_dataset_content(history_id, hid=13)
            t4 = self.dataset_populator.get_history_dataset_content(history_id, hid=16)
            self.assertEqual(r1, t1)
            self.assertEqual(r2, t2)
            self.assertEqual(r3, t3)
            self.assertEqual(r4, t4)

    @skip_without_tool("validation_default")
    def test_parameter_substitution_sanitization(self):
        substitions = dict(input1="\" ; echo \"moo")
        run_workflow_response, history_id = self._run_validation_workflow_with_substitions(substitions)

        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        self.assertEqual("__dq__ X echo __dq__moo\n", self.dataset_populator.get_history_dataset_content(history_id, hid=1))

    @skip_without_tool("validation_repeat")
    def test_parameter_substitution_validation_value_errors_0(self):
        with self.dataset_populator.test_history() as history_id:
            workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
steps:
  validation:
    tool_id: validation_repeat
    state:
      r2:
        - text: "abd"
""")
            workflow_request = dict(
                history="hist_id=%s" % history_id,
                parameters=dumps(dict(validation_repeat={"r2_0|text": ""}))
            )
            url = "workflows/%s/invocations" % workflow_id
            invocation_response = self._post(url, data=workflow_request)
            # Take a valid stat and make it invalid, assert workflow won't run.
            self._assert_status_code_is(invocation_response, 400)

    @skip_without_tool("validation_default")
    def test_parameter_substitution_validation_value_errors_1(self):
        substitions = dict(select_param="\" ; echo \"moo")
        run_workflow_response, history_id = self._run_validation_workflow_with_substitions(substitions)

        self._assert_status_code_is(run_workflow_response, 400)

    @skip_without_tool("validation_repeat")
    def test_workflow_import_state_validation_1(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs("""
class: GalaxyWorkflow
steps:
  validation:
    tool_id: validation_repeat
    state:
      r2:
      - text: ""
""", history_id=history_id, wait=False, expected_response=400)

    def _run_validation_workflow_with_substitions(self, substitions):
        workflow = self.workflow_populator.load_workflow_from_resource("test_workflow_validation_1")
        uploaded_workflow_id = self.workflow_populator.create_workflow(workflow)
        history_id = self.dataset_populator.new_history()
        workflow_request = dict(
            history="hist_id=%s" % history_id,
            workflow_id=uploaded_workflow_id,
            parameters=dumps(dict(validation_default=substitions))
        )
        run_workflow_response = self._post("workflows", data=workflow_request)
        return run_workflow_response, history_id

    @skip_without_tool("random_lines1")
    def test_run_replace_params_by_steps(self):
        workflow_request, history_id, steps = self._setup_random_x2_workflow_steps("test_for_replace_step_params")
        params = dumps({str(steps[1]["id"]): dict(num_lines=5)})
        workflow_request["parameters"] = params
        run_workflow_response = self._post("workflows", data=workflow_request)
        self._assert_status_code_is(run_workflow_response, 200)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        # Would be 8 and 6 without modification
        self.__assert_lines_hid_line_count_is(history_id, 2, 8)
        self.__assert_lines_hid_line_count_is(history_id, 3, 5)

    @skip_without_tool("random_lines1")
    def test_run_replace_params_nested(self):
        workflow_request, history_id, steps = self._setup_random_x2_workflow_steps("test_for_replace_step_params_nested")
        seed_source = dict(
            seed_source_selector="set_seed",
            seed="moo",
        )
        params = dumps({str(steps[0]["id"]): dict(num_lines=1, seed_source=seed_source),
                        str(steps[1]["id"]): dict(num_lines=1, seed_source=seed_source)})
        workflow_request["parameters"] = params
        run_workflow_response = self._post("workflows", data=workflow_request)
        self._assert_status_code_is(run_workflow_response, 200)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        self.assertEqual("2\n", self.dataset_populator.get_history_dataset_content(history_id))

    @skip_without_tool("random_lines1")
    def test_run_replace_params_nested_normalized(self):
        workflow_request, history_id, steps = self._setup_random_x2_workflow_steps("test_for_replace_step_normalized_params_nested")
        parameters = {
            "num_lines": 1,
            "seed_source|seed_source_selector": "set_seed",
            "seed_source|seed": "moo",
        }
        params = dumps({str(steps[0]["id"]): parameters,
                        str(steps[1]["id"]): parameters})
        workflow_request["parameters"] = params
        workflow_request["parameters_normalized"] = False
        run_workflow_response = self._post("workflows", data=workflow_request)
        self._assert_status_code_is(run_workflow_response, 200)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        self.assertEqual("2\n", self.dataset_populator.get_history_dataset_content(history_id))

    @skip_without_tool("random_lines1")
    def test_run_replace_params_over_default(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(WORKFLOW_ONE_STEP_DEFAULT, test_data="""
step_parameters:
  '1':
    num_lines: 4
input:
  value: 1.bed
  type: File
""", history_id=history_id, wait=True, assert_ok=True, round_trip_format_conversion=True)
            result = self.dataset_populator.get_history_dataset_content(history_id)
            assert result.count("\n") == 4

    @skip_without_tool("random_lines1")
    def test_defaults_editor(self):
        workflow_id = self._upload_yaml_workflow(WORKFLOW_ONE_STEP_DEFAULT, publish=True)
        workflow_object = self._download_workflow(workflow_id, style="editor")
        put_response = self._update_workflow(workflow_id, workflow_object)
        assert put_response.status_code == 200

    @skip_without_tool("random_lines1")
    def test_run_replace_params_over_default_delayed(self):
        with self.dataset_populator.test_history() as history_id:
            run_summary = self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input: data
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: input
  the_pause:
    type: pause
    in:
      input: first_cat/out_file1
  randomlines:
    tool_id: random_lines1
    in:
      input: the_pause
      num_lines:
        default: 6
""", test_data="""
step_parameters:
  '3':
    num_lines: 4
input:
  value: 1.bed
  type: File
""", history_id=history_id, wait=False)
            wait_on(lambda: len(self._history_jobs(history_id)) >= 2 or None, "history jobs")
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            workflow_id = run_summary.workflow_id
            invocation_id = run_summary.invocation_id

            self.__review_paused_steps(workflow_id, invocation_id, order_index=2, action=True)
            self.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)

            result = self.dataset_populator.get_history_dataset_content(history_id)
            assert result.count("\n") == 4

    def test_pja_import_export(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_pja_import", add_pja=True)
        uploaded_workflow_id = self.workflow_populator.create_workflow(workflow)
        downloaded_workflow = self._download_workflow(uploaded_workflow_id)
        self._assert_has_keys(downloaded_workflow["steps"], "0", "1", "2")
        pjas = list(downloaded_workflow["steps"]["2"]["post_job_actions"].values())
        assert len(pjas) == 1, len(pjas)
        pja = pjas[0]
        self._assert_has_keys(pja, "action_type", "output_name", "action_arguments")

    @skip_without_tool("cat1")
    def test_only_own_invocations_indexed_and_accessible(self):
        workflow_id, usage = self._run_workflow_once_get_invocation("test_usage")
        with self._different_user():
            usage_details_response = self._get("workflows/%s/usage/%s" % (workflow_id, usage["id"]))
            self._assert_status_code_is(usage_details_response, 403)

        invocation_ids = self._all_user_invocation_ids()
        assert usage["id"] in invocation_ids

        with self._different_user():
            invocation_ids = self._all_user_invocation_ids()
            assert usage["id"] not in invocation_ids

    @skip_without_tool("cat1")
    def test_invocation_usage(self):
        workflow_id, usage = self._run_workflow_once_get_invocation("test_usage")
        invocation_id = usage["id"]
        usage_details = self._invocation_details(workflow_id, invocation_id)
        # Assert some high-level things about the structure of data returned.
        self._assert_has_keys(usage_details, "inputs", "steps", "workflow_id", "history_id")

        # Check invocations for this workflow invocation by history and regardless of history.
        history_invocations_response = self._get("invocations", {"history_id": usage_details["history_id"]})
        self._assert_status_code_is(history_invocations_response, 200)
        assert len(history_invocations_response.json()) == 1
        assert history_invocations_response.json()[0]["id"] == invocation_id

        # Check history invocations for this workflow invocation.
        invocation_ids = self._all_user_invocation_ids()
        assert invocation_id in invocation_ids

        # Wait for the invocation to be fully scheduled, so we have details on all steps.
        self._wait_for_invocation_state(workflow_id, invocation_id, 'scheduled')
        usage_details = self._invocation_details(workflow_id, invocation_id)

        invocation_steps = usage_details["steps"]
        invocation_input_step, invocation_tool_step = None, None
        for invocation_step in invocation_steps:
            self._assert_has_keys(invocation_step, "workflow_step_id", "order_index", "id")
            order_index = invocation_step["order_index"]
            assert order_index in [0, 1, 2], order_index
            if order_index == 0:
                invocation_input_step = invocation_step
            elif order_index == 2:
                invocation_tool_step = invocation_step

        # Tool steps have non-null job_ids (deprecated though they may be)
        assert invocation_input_step.get("job_id", None) is None
        job_id = invocation_tool_step.get("job_id", None)
        assert job_id is not None

        invocation_tool_step_id = invocation_tool_step["id"]
        invocation_tool_step_response = self._get("workflows/%s/invocations/%s/steps/%s" % (workflow_id, invocation_id, invocation_tool_step_id))
        self._assert_status_code_is(invocation_tool_step_response, 200)
        self._assert_has_keys(invocation_tool_step_response.json(), "id", "order_index", "job_id")

        assert invocation_tool_step_response.json()["job_id"] == job_id

    def test_invocation_with_collection_mapping(self):
        workflow_id, invocation_id = self._run_mapping_workflow()

        usage_details = self._invocation_details(workflow_id, invocation_id)
        # Assert some high-level things about the structure of data returned.
        self._assert_has_keys(usage_details, "inputs", "steps", "workflow_id")

        invocation_steps = usage_details["steps"]
        invocation_input_step, invocation_tool_step = None, None
        for invocation_step in invocation_steps:
            self._assert_has_keys(invocation_step, "workflow_step_id", "order_index", "id")
            order_index = invocation_step["order_index"]
            assert order_index in [0, 1]
            if invocation_step["order_index"] == 0:
                assert invocation_input_step is None
                invocation_input_step = invocation_step
            else:
                assert invocation_tool_step is None
                invocation_tool_step = invocation_step

        # Tool steps have non-null job_ids (deprecated though they may be)
        assert invocation_input_step.get("job_id", None) is None
        assert invocation_tool_step.get("job_id", None) is None
        assert invocation_tool_step["state"] == "scheduled"

        usage_details = self._invocation_details(workflow_id, invocation_id, legacy_job_state="true")
        # Assert some high-level things about the structure of data returned.
        self._assert_has_keys(usage_details, "inputs", "steps", "workflow_id")

        invocation_steps = usage_details["steps"]
        invocation_input_step = None
        invocation_tool_steps = []
        for invocation_step in invocation_steps:
            self._assert_has_keys(invocation_step, "workflow_step_id", "order_index", "id")
            order_index = invocation_step["order_index"]
            assert order_index in [0, 1]
            if invocation_step["order_index"] == 0:
                assert invocation_input_step is None
                invocation_input_step = invocation_step
            else:
                invocation_tool_steps.append(invocation_step)

        assert len(invocation_tool_steps) == 2
        assert invocation_tool_steps[0]["state"] == "ok"

    def _run_mapping_workflow(self):
        history_id = self.dataset_populator.new_history()
        summary = self._run_jobs("""
class: GalaxyWorkflow
inputs:
  input_c: collection
steps:
  cat1:
    tool_id: cat1
    in:
       input1: input_c
""", test_data="""
input_c:
  type: list
  elements:
    - identifier: i1
      content: "0"
    - identifier: i2
      content: "1"
""", history_id=history_id, wait=True, assert_ok=True)
        workflow_id = summary.workflow_id
        invocation_id = summary.invocation_id
        return workflow_id, invocation_id

    @skip_without_tool("cat1")
    def test_invocations_accessible_imported_workflow(self):
        workflow_id = self.workflow_populator.simple_workflow("test_usage", publish=True)
        with self._different_user():
            other_import_response = self.__import_workflow(workflow_id)
            self._assert_status_code_is(other_import_response, 200)
            other_id = other_import_response.json()["id"]
            workflow_request, history_id = self._setup_workflow_run(workflow_id=other_id)
            response = self._get("workflows/%s/usage" % other_id)
            self._assert_status_code_is(response, 200)
            assert len(response.json()) == 0
            run_workflow_response = self._post("workflows", data=workflow_request)
            self._assert_status_code_is(run_workflow_response, 200)
            run_workflow_response = run_workflow_response.json()
            invocation_id = run_workflow_response['id']
            usage_details_response = self._get("workflows/%s/usage/%s" % (other_id, invocation_id))
            self._assert_status_code_is(usage_details_response, 200)

    @skip_without_tool("cat1")
    def test_invocations_accessible_published_workflow(self):
        workflow_id = self.workflow_populator.simple_workflow("test_usage", publish=True)
        with self._different_user():
            workflow_request, history_id = self._setup_workflow_run(workflow_id=workflow_id)
            workflow_request['workflow_id'] = workflow_request.pop('workflow_id')
            response = self._get("workflows/%s/usage" % workflow_id)
            self._assert_status_code_is(response, 200)
            assert len(response.json()) == 0
            run_workflow_response = self._post("workflows", data=workflow_request)
            self._assert_status_code_is(run_workflow_response, 200)
            run_workflow_response = run_workflow_response.json()
            invocation_id = run_workflow_response['id']
            usage_details_response = self._get("workflows/%s/usage/%s" % (workflow_id, invocation_id))
            self._assert_status_code_is(usage_details_response, 200)

    @skip_without_tool("cat1")
    def test_invocations_not_accessible_by_different_user_for_published_workflow(self):
        workflow_id = self.workflow_populator.simple_workflow("test_usage", publish=True)
        workflow_request, history_id = self._setup_workflow_run(workflow_id=workflow_id)
        workflow_request['workflow_id'] = workflow_request.pop('workflow_id')
        response = self._get("workflows/%s/usage" % workflow_id)
        self._assert_status_code_is(response, 200)
        assert len(response.json()) == 0
        run_workflow_response = self._post("workflows", data=workflow_request)
        self._assert_status_code_is(run_workflow_response, 200)
        run_workflow_response = run_workflow_response.json()
        invocation_id = run_workflow_response['id']
        with self._different_user():
            usage_details_response = self._get("workflows/%s/usage/%s" % (workflow_id, invocation_id))
            self._assert_status_code_is(usage_details_response, 403)

    def _invoke_paused_workflow(self, history_id):
        workflow = self.workflow_populator.load_workflow_from_resource("test_workflow_pause")
        workflow_id = self.workflow_populator.create_workflow(workflow)
        hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
        index_map = {
            '0': self._ds_entry(hda1),
        }
        invocation_id = self.__invoke_workflow(
            history_id,
            workflow_id,
            index_map,
        )
        return workflow_id, invocation_id

    def _wait_for_invocation_non_new(self, workflow_id, invocation_id):
        target_state_reached = False
        for i in range(50):
            invocation = self._invocation_details(workflow_id, invocation_id)
            if invocation['state'] != 'new':
                target_state_reached = True
                break

            time.sleep(.25)

        return target_state_reached

    def _assert_invocation_non_terminal(self, workflow_id, invocation_id):
        invocation = self._invocation_details(workflow_id, invocation_id)
        assert invocation['state'] in ['ready', 'new'], invocation

    def _wait_for_invocation_state(self, workflow_id, invocation_id, target_state):
        target_state_reached = False
        for i in range(25):
            invocation = self._invocation_details(workflow_id, invocation_id)
            if invocation['state'] == target_state:
                target_state_reached = True
                break

            time.sleep(.5)

        return target_state_reached

    def _update_workflow(self, workflow_id, workflow_object):
        return self.workflow_populator.update_workflow(workflow_id, workflow_object)

    def _invocation_step_details(self, workflow_id, invocation_id, step_id):
        invocation_step_response = self._get("workflows/%s/usage/%s/steps/%s" % (workflow_id, invocation_id, step_id))
        self._assert_status_code_is(invocation_step_response, 200)
        invocation_step_details = invocation_step_response.json()
        return invocation_step_details

    def _execute_invocation_step_action(self, workflow_id, invocation_id, step_id, action):
        raw_url = "workflows/%s/usage/%s/steps/%s" % (workflow_id, invocation_id, step_id)
        url = self._api_url(raw_url, use_key=True)
        payload = dumps(dict(action=action))
        action_response = put(url, data=payload)
        self._assert_status_code_is(action_response, 200)
        invocation_step_details = action_response.json()
        return invocation_step_details

    def _run_workflow_once_get_invocation(self, name):
        workflow = self.workflow_populator.load_workflow(name=name)
        workflow_request, history_id = self._setup_workflow_run(workflow)
        workflow_id = workflow_request["workflow_id"]
        response = self._get("workflows/%s/usage" % workflow_id)
        self._assert_status_code_is(response, 200)
        assert len(response.json()) == 0
        run_workflow_response = self._post("workflows", data=workflow_request)
        self._assert_status_code_is(run_workflow_response, 200)

        response = self._get("workflows/%s/usage" % workflow_id)
        self._assert_status_code_is(response, 200)
        usages = response.json()
        assert len(usages) == 1
        return workflow_id, usages[0]

    def _setup_random_x2_workflow_steps(self, name):
        workflow_request, history_id = self._setup_random_x2_workflow("test_for_replace_step_params")
        random_line_steps = self._random_lines_steps(workflow_request)
        return workflow_request, history_id, random_line_steps

    def _random_lines_steps(self, workflow_request):
        workflow_summary_response = self._get("workflows/%s" % workflow_request["workflow_id"])
        self._assert_status_code_is(workflow_summary_response, 200)
        steps = workflow_summary_response.json()["steps"]
        return sorted((step for step in steps.values() if step["tool_id"] == "random_lines1"), key=lambda step: step["id"])

    def _setup_random_x2_workflow(self, name):
        workflow = self.workflow_populator.load_random_x2_workflow(name)
        uploaded_workflow_id = self.workflow_populator.create_workflow(workflow)
        workflow_inputs = self._workflow_inputs(uploaded_workflow_id)
        key = next(iter(workflow_inputs.keys()))
        history_id = self.dataset_populator.new_history()
        ten_lines = "\n".join(str(_) for _ in range(10))
        hda1 = self.dataset_populator.new_dataset(history_id, content=ten_lines)
        workflow_request = dict(
            history="hist_id=%s" % history_id,
            workflow_id=uploaded_workflow_id,
            ds_map=dumps({
                key: self._ds_entry(hda1),
            }),
        )
        return workflow_request, history_id

    def __review_paused_steps(self, uploaded_workflow_id, invocation_id, order_index, action=True):
        invocation = self._invocation_details(uploaded_workflow_id, invocation_id)
        invocation_steps = invocation["steps"]
        pause_steps = [s for s in invocation_steps if s['order_index'] == order_index]
        for pause_step in pause_steps:
            pause_step_id = pause_step['id']

            self._execute_invocation_step_action(uploaded_workflow_id, invocation_id, pause_step_id, action=action)

    def __assert_lines_hid_line_count_is(self, history, hid, lines):
        contents_url = "histories/%s/contents" % history
        history_contents = self.__history_contents(history)
        hda_summary = next(hc for hc in history_contents if hc["hid"] == hid)
        hda_info_response = self._get("%s/%s" % (contents_url, hda_summary["id"]))
        self._assert_status_code_is(hda_info_response, 200)
        self.assertEqual(hda_info_response.json()["metadata_data_lines"], lines)

    def __history_contents(self, history_id):
        contents_url = "histories/%s/contents" % history_id
        history_contents_response = self._get(contents_url)
        self._assert_status_code_is(history_contents_response, 200)
        return history_contents_response.json()

    def __invoke_workflow(self, *args, **kwds):
        return self.workflow_populator.invoke_workflow(*args, **kwds)

    def __import_workflow(self, workflow_id, deprecated_route=False):
        if deprecated_route:
            route = "workflows/import"
            import_data = dict(
                workflow_id=workflow_id,
            )
        else:
            route = "workflows"
            import_data = dict(
                shared_workflow_id=workflow_id,
            )
        return self._post(route, import_data)

    def _show_workflow(self, workflow_id):
        show_response = self._get("workflows/%s" % workflow_id)
        self._assert_status_code_is(show_response, 200)
        return show_response.json()

    def _assert_looks_like_instance_workflow_representation(self, workflow):
        self._assert_has_keys(
            workflow,
            'url',
            'owner',
            'inputs',
            'annotation',
            'steps'
        )
        for step in workflow["steps"].values():
            self._assert_has_keys(
                step,
                'id',
                'type',
                'tool_id',
                'tool_version',
                'annotation',
                'tool_inputs',
                'input_steps',
            )

    def _all_user_invocation_ids(self):
        all_invocations_for_user = self._get("invocations")
        self._assert_status_code_is(all_invocations_for_user, 200)
        invocation_ids = [i["id"] for i in all_invocations_for_user.json()]
        return invocation_ids
