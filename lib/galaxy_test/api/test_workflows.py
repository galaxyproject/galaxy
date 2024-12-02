import base64
import io
import json
import os
import shutil
import time
from json import dumps
from tempfile import mkdtemp
from typing import (
    Any,
    cast,
    Dict,
    Optional,
    Tuple,
    Union,
)
from uuid import uuid4

import pytest
import yaml
from requests import (
    delete,
    get,
    post,
    put,
)

from galaxy.exceptions import error_codes
from galaxy.util import UNKNOWN
from galaxy_test.base import rules_test_data
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    RunJobsSummary,
    skip_without_tool,
    wait_on,
    workflow_str,
    WorkflowPopulator,
)
from galaxy_test.base.workflow_fixtures import (
    NESTED_WORKFLOW_WITH_CONDITIONAL_SUBWORKFLOW_AND_DISCONNECTED_MAP_OVER_SOURCE,
    WORKFLOW_FLAT_CROSS_PRODUCT,
    WORKFLOW_INPUTS_AS_OUTPUTS,
    WORKFLOW_NESTED_REPLACEMENT_PARAMETER,
    WORKFLOW_NESTED_RUNTIME_PARAMETER,
    WORKFLOW_NESTED_SIMPLE,
    WORKFLOW_ONE_STEP_DEFAULT,
    WORKFLOW_OPTIONAL_FALSE_INPUT_COLLECTION,
    WORKFLOW_OPTIONAL_FALSE_INPUT_DATA,
    WORKFLOW_OPTIONAL_INPUT_DELAYED_SCHEDULING,
    WORKFLOW_OPTIONAL_TRUE_INPUT_COLLECTION,
    WORKFLOW_OPTIONAL_TRUE_INPUT_DATA,
    WORKFLOW_PARAMETER_INPUT_INTEGER_DEFAULT,
    WORKFLOW_PARAMETER_INPUT_INTEGER_OPTIONAL,
    WORKFLOW_PARAMETER_INPUT_INTEGER_REQUIRED,
    WORKFLOW_RENAME_ON_INPUT,
    WORKFLOW_RUNTIME_PARAMETER_AFTER_PAUSE,
    WORKFLOW_WITH_BAD_COLUMN_PARAMETER,
    WORKFLOW_WITH_BAD_COLUMN_PARAMETER_GOOD_TEST_DATA,
    WORKFLOW_WITH_CUSTOM_REPORT_1,
    WORKFLOW_WITH_CUSTOM_REPORT_1_TEST_DATA,
    WORKFLOW_WITH_DEFAULT_FILE_DATASET_INPUT,
    WORKFLOW_WITH_DYNAMIC_OUTPUT_COLLECTION,
    WORKFLOW_WITH_MAPPED_OUTPUT_COLLECTION,
    WORKFLOW_WITH_OUTPUT_COLLECTION,
    WORKFLOW_WITH_OUTPUT_COLLECTION_MAPPING,
    WORKFLOW_WITH_RULES_1,
    WORKFLOW_WITH_STEP_DEFAULT_FILE_DATASET_INPUT,
)
from ._framework import ApiTestCase
from .sharable import SharingApiTests

WORKFLOW_SIMPLE = """
class: GalaxyWorkflow
name: Simple Workflow
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
"""

NESTED_WORKFLOW_AUTO_LABELS_MODERN_SYNTAX = """
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
        - outputSource: 1/out_file1
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
    in:
      input1: nested_workflow/1:out_file1
      queries_0|input2: nested_workflow/1:out_file1
"""


class RunsWorkflowFixtures:
    workflow_populator: WorkflowPopulator

    def _run_workflow_with_inputs_as_outputs(self, history_id: str) -> RunJobsSummary:
        summary = self.workflow_populator.run_workflow(
            WORKFLOW_INPUTS_AS_OUTPUTS,
            test_data={"input1": "hello world", "text_input": {"value": "A text variable", "type": "raw"}},
            history_id=history_id,
        )
        return summary

    def _run_workflow_with_output_collections(self, history_id: str) -> RunJobsSummary:
        summary = self.workflow_populator.run_workflow(
            WORKFLOW_WITH_MAPPED_OUTPUT_COLLECTION,
            test_data="""
input1:
  collection_type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
""",
            history_id=history_id,
            round_trip_format_conversion=True,
        )
        return summary

    def _run_workflow_with_runtime_data_column_parameter(self, history_id: str) -> RunJobsSummary:
        return self.workflow_populator.run_workflow(
            WORKFLOW_WITH_BAD_COLUMN_PARAMETER,
            test_data=WORKFLOW_WITH_BAD_COLUMN_PARAMETER_GOOD_TEST_DATA,
            history_id=history_id,
        )

    def _run_workflow_once_get_invocation(self, name: str):
        workflow = self.workflow_populator.load_workflow(name=name)
        workflow_request, history_id, workflow_id = self.workflow_populator.setup_workflow_run(workflow)
        usages = self.workflow_populator.workflow_invocations(workflow_id)
        assert len(usages) == 0
        self.workflow_populator.invoke_workflow_raw(workflow_id, workflow_request, assert_ok=True)
        usages = self.workflow_populator.workflow_invocations(workflow_id)
        assert len(usages) == 1
        return workflow_id, usages[0]


class BaseWorkflowsApiTestCase(ApiTestCase, RunsWorkflowFixtures):
    # TODO: Find a new file for this class.
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def _assert_user_has_workflow_with_name(self, name):
        names = self._workflow_names()
        assert name in names, f"No workflows with name {name} in users workflows <{names}>"

    def _workflow_names(self):
        index_response = self._get("workflows")
        self._assert_status_code_is(index_response, 200)
        names = [w["name"] for w in index_response.json()]
        return names

    def import_workflow(self, workflow, **kwds):
        upload_response = self.workflow_populator.import_workflow(workflow, **kwds)
        return upload_response

    def _upload_yaml_workflow(self, has_yaml, **kwds) -> str:
        return self.workflow_populator.upload_yaml_workflow(has_yaml, **kwds)

    def _setup_workflow_run(
        self,
        workflow: Optional[Dict[str, Any]] = None,
        inputs_by: str = "step_id",
        history_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], str, str]:
        return self.workflow_populator.setup_workflow_run(workflow, inputs_by, history_id, workflow_id)

    def _ds_entry(self, history_content):
        return self.dataset_populator.ds_entry(history_content)

    def _invocation_details(self, workflow_id, invocation_id, **kwds):
        invocation_details_response = self._get(f"workflows/{workflow_id}/usage/{invocation_id}", data=kwds)
        self._assert_status_code_is(invocation_details_response, 200)
        invocation_details = invocation_details_response.json()
        return invocation_details

    def _run_jobs(self, has_workflow, history_id: str, **kwds) -> Union[Dict[str, Any], RunJobsSummary]:
        return self.workflow_populator.run_workflow(has_workflow, history_id=history_id, **kwds)

    def _run_workflow(self, has_workflow, history_id: str, **kwds) -> RunJobsSummary:
        assert "expected_response" not in kwds
        run_summary = self.workflow_populator.run_workflow(has_workflow, history_id=history_id, **kwds)
        return cast(RunJobsSummary, run_summary)

    def _history_jobs(self, history_id):
        return self._get("jobs", {"history_id": history_id, "order_by": "create_time"}).json()

    def _assert_history_job_count(self, history_id, n):
        jobs = self._history_jobs(history_id)
        assert len(jobs) == n

    def _download_workflow(self, workflow_id, style=None, history_id=None):
        return self.workflow_populator.download_workflow(workflow_id, style=style, history_id=history_id)

    def _assert_is_runtime_input(self, tool_state_value):
        if not isinstance(tool_state_value, dict):
            tool_state_value = json.loads(tool_state_value)

        assert isinstance(tool_state_value, dict)
        assert "__class__" in tool_state_value
        assert tool_state_value["__class__"] == "RuntimeValue"


class ChangeDatatypeTests:
    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator

    def test_assign_column_pja(self):
        with self.dataset_populator.test_history() as history_id:
            self.workflow_populator.run_workflow(
                """
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
        change_datatype: bed
        set_columns:
          chromCol: 1
          endCol: 2
          startCol: 3
""",
                test_data="""
input1:
  value: 1.bed
  type: File
""",
                history_id=history_id,
            )
            details_dataset_new_col = self.dataset_populator.get_history_dataset_details(
                history_id, hid=2, wait=True, assert_ok=True
            )
            assert details_dataset_new_col["history_content_type"] == "dataset", details_dataset_new_col
            assert details_dataset_new_col["metadata_endCol"] == 2
            assert details_dataset_new_col["metadata_startCol"] == 3


class TestWorkflowSharingApi(ApiTestCase, SharingApiTests):
    api_name = "workflows"

    def create(self, name: str) -> str:
        """Creates a shareable resource with the given name and returns it's ID.

        :param name: The name of the shareable resource to create.
        :return: The ID of the resource.
        """
        workflow = self.workflow_populator.load_workflow(name=name)
        data = dict(
            workflow=dumps(workflow),
        )
        route = "workflows"
        upload_response = self._post(route, data=data)

        self._assert_status_code_is(upload_response, 200)
        return upload_response.json()["id"]

    def setUp(self):
        super().setUp()
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)


# Workflow API TODO:
# - Allow history_id as param to workflow run action. (hist_id)
# - Allow post to workflows/<workflow_id>/run in addition to posting to
#    /workflows with id in payload.
# - Much more testing obviously, always more testing.
class TestWorkflowsApi(BaseWorkflowsApiTestCase, ChangeDatatypeTests):
    dataset_populator: DatasetPopulator

    def test_show_valid(self):
        workflow_id = self.workflow_populator.simple_workflow("dummy")
        workflow_id = self.workflow_populator.simple_workflow("test_regular")
        show_response = self._get(f"workflows/{workflow_id}", {"style": "instance"})
        workflow = show_response.json()
        self._assert_looks_like_instance_workflow_representation(workflow)
        assert len(workflow["steps"]) == 3
        assert sorted(step["id"] for step in workflow["steps"].values()) == [0, 1, 2]

        show_response = self._get(f"workflows/{workflow_id}", {"legacy": True})
        workflow = show_response.json()
        self._assert_looks_like_instance_workflow_representation(workflow)
        assert len(workflow["steps"]) == 3
        # Can't reay say what the legacy IDs are but must be greater than 3 because dummy
        # workflow was created first in this instance.
        assert sorted(step["id"] for step in workflow["steps"].values()) != [0, 1, 2]

    def test_show_subworkflow(self):
        workflow_id = self.workflow_populator.upload_yaml_workflow(WORKFLOW_NESTED_SIMPLE)
        workflow = self._get(f"workflows/{workflow_id}", {"style": "instance"}).json()
        assert isinstance(workflow["id"], str)
        subworkflow_step = workflow["steps"]["2"]
        assert subworkflow_step["type"] == "subworkflow"
        assert isinstance(subworkflow_step["workflow_id"], str)
        self._get(f"workflows/{subworkflow_step['workflow_id']}", {"style": "instance"}).json()

    def test_show_invalid_key_is_400(self):
        show_response = self._get(f"workflows/{self._random_key()}")
        self._assert_status_code_is(show_response, 400)

    def test_cannot_show_private_workflow(self):
        workflow_id = self.workflow_populator.simple_workflow("test_not_importable")
        with self._different_user():
            show_response = self._get(f"workflows/{workflow_id}")
            self._assert_status_code_is(show_response, 403)

            # Try as anonymous user
            workflows_url = self._api_url(f"workflows/{workflow_id}")
            assert get(workflows_url).status_code == 403

    def test_cannot_download_private_workflow(self):
        workflow_id = self.workflow_populator.simple_workflow("test_not_downloadable")
        with self._different_user():
            with pytest.raises(AssertionError) as excinfo:
                self._download_workflow(workflow_id)
            assert "403" in str(excinfo.value)
        workflows_url = self._api_url(f"workflows/{workflow_id}/download")
        assert get(workflows_url).status_code == 403

    def test_anon_can_download_importable_workflow(self):
        workflow_id = self.workflow_populator.simple_workflow("test_downloadable", importable=True)
        workflows_url = self._api_url(f"workflows/{workflow_id}/download")
        response = get(workflows_url)
        response.raise_for_status()
        assert response.json()["a_galaxy_workflow"] == "true"

    def test_anon_can_download_public_workflow(self):
        workflow_id = self.workflow_populator.simple_workflow("test_downloadable", publish=True)
        workflows_url = self._api_url(f"workflows/{workflow_id}/download")
        response = get(workflows_url)
        response.raise_for_status()
        assert response.json()["a_galaxy_workflow"] == "true"

    def test_anon_can_see_workflow_preview(self):
        workflow_id = self.workflow_populator.simple_workflow(name="test_preview", importable=True)
        workflows_url = self._api_url(f"workflows/{workflow_id}/download", params={"style": "preview"})
        response = get(workflows_url)
        response.raise_for_status()
        assert response.json()["name"] == "test_preview"

    def test_delete(self):
        workflow_id = self.workflow_populator.simple_workflow("test_delete")
        workflow_name = "test_delete"
        self._assert_user_has_workflow_with_name(workflow_name)
        workflow_url = self._api_url(f"workflows/{workflow_id}", use_key=True)
        delete_response = delete(workflow_url)
        self._assert_status_code_is(delete_response, 204)
        # Make sure workflow is no longer in index by default.
        assert workflow_name not in self._workflow_names()

    def test_other_cannot_delete(self):
        workflow_id = self.workflow_populator.simple_workflow("test_other_delete")
        with self._different_user():
            workflow_url = self._api_url(f"workflows/{workflow_id}", use_key=True)
            delete_response = delete(workflow_url)
            self._assert_status_code_is(delete_response, 403)

    def test_undelete(self):
        workflow_id = self.workflow_populator.simple_workflow("test_undelete")
        workflow_name = "test_undelete"
        self._assert_user_has_workflow_with_name(workflow_name)
        workflow_delete_url = self._api_url(f"workflows/{workflow_id}", use_key=True)
        delete(workflow_delete_url)
        workflow_undelete_url = self._api_url(f"workflows/{workflow_id}/undelete", use_key=True)
        undelete_response = post(workflow_undelete_url)
        self._assert_status_code_is(undelete_response, 204)
        assert workflow_name in self._workflow_names()

    def test_other_cannot_undelete(self):
        workflow_id = self.workflow_populator.simple_workflow("test_other_undelete")
        workflow_delete_url = self._api_url(f"workflows/{workflow_id}", use_key=True)
        delete(workflow_delete_url)
        with self._different_user():
            workflow_undelete_url = self._api_url(f"workflows/{workflow_id}/undelete", use_key=True)
            undelete_response = post(workflow_undelete_url)
            self._assert_status_code_is(undelete_response, 403)

    def test_index(self):
        index_response = self._get("workflows")
        self._assert_status_code_is(index_response, 200)
        assert isinstance(index_response.json(), list)

    def test_index_deleted(self):
        workflow_id = self.workflow_populator.simple_workflow("test_delete")
        workflow_index = self._get("workflows").json()
        assert [w for w in workflow_index if w["id"] == workflow_id]
        workflow_url = self._api_url(f"workflows/{workflow_id}", use_key=True)
        delete_response = delete(workflow_url)
        self._assert_status_code_is(delete_response, 204)
        workflow_index = self._get("workflows").json()
        assert not [w for w in workflow_index if w["id"] == workflow_id]
        workflow_index = self._get("workflows?show_deleted=true").json()
        assert [w for w in workflow_index if w["id"] == workflow_id]
        workflow_index = self._get("workflows?show_deleted=false").json()
        assert not [w for w in workflow_index if w["id"] == workflow_id]

    def test_index_hidden(self):
        workflow_id = self.workflow_populator.simple_workflow("test_delete")
        workflow_index = self._get("workflows").json()
        workflow = [w for w in workflow_index if w["id"] == workflow_id][0]
        workflow["hidden"] = True
        update_response = self.workflow_populator.update_workflow(workflow_id, workflow)
        self._assert_status_code_is(update_response, 200)
        assert update_response.json()["hidden"]
        workflow_index = self._get("workflows").json()
        assert not [w for w in workflow_index if w["id"] == workflow_id]
        workflow_index = self._get("workflows?show_hidden=true").json()
        assert [w for w in workflow_index if w["id"] == workflow_id]
        workflow_index = self._get("workflows?show_hidden=false").json()
        assert not [w for w in workflow_index if w["id"] == workflow_id]

    def test_index_ordering(self):
        # ordered by update_time on the stored workflows with all user's workflows
        # before workflows shared with user.
        my_workflow_id_1 = self.workflow_populator.simple_workflow("mine_1")
        my_workflow_id_2 = self.workflow_populator.simple_workflow("mine_2")
        my_email = self.dataset_populator.user_email()
        with self._different_user():
            their_workflow_id_1 = self.workflow_populator.simple_workflow("theirs_1")
            their_workflow_id_2 = self.workflow_populator.simple_workflow("theirs_2")
            self.workflow_populator.share_with_user(their_workflow_id_1, my_email)
            self.workflow_populator.share_with_user(their_workflow_id_2, my_email)
        index_ids = self.workflow_populator.index_ids()
        assert index_ids.index(my_workflow_id_1) >= 0
        assert index_ids.index(my_workflow_id_2) >= 0
        assert index_ids.index(their_workflow_id_1) >= 0
        assert index_ids.index(their_workflow_id_2) >= 0

        # ordered by update time...
        assert index_ids.index(my_workflow_id_2) < index_ids.index(my_workflow_id_1)
        assert index_ids.index(their_workflow_id_2) < index_ids.index(their_workflow_id_1)

        # my workflows before theirs...
        assert index_ids.index(my_workflow_id_1) < index_ids.index(their_workflow_id_1)
        assert index_ids.index(my_workflow_id_2) < index_ids.index(their_workflow_id_1)
        assert index_ids.index(my_workflow_id_1) < index_ids.index(their_workflow_id_2)
        assert index_ids.index(my_workflow_id_2) < index_ids.index(their_workflow_id_2)

        actions = [
            {"action_type": "update_name", "name": "mine_1(updated)"},
        ]
        refactor_response = self.workflow_populator.refactor_workflow(my_workflow_id_1, actions)
        refactor_response.raise_for_status()
        index_ids = self.workflow_populator.index_ids()

        # after an update to workflow 1, it now comes before workflow 2
        assert index_ids.index(my_workflow_id_1) < index_ids.index(my_workflow_id_2)

    def test_index_sort_by(self):
        my_workflow_id_y = self.workflow_populator.simple_workflow("y_1")
        my_workflow_id_z = self.workflow_populator.simple_workflow("z_2")
        index_ids = self.workflow_populator.index_ids()
        assert index_ids.index(my_workflow_id_z) < index_ids.index(my_workflow_id_y)
        index_ids = self.workflow_populator.index_ids(sort_by="create_time", sort_desc=True)
        assert index_ids.index(my_workflow_id_z) < index_ids.index(my_workflow_id_y)
        index_ids = self.workflow_populator.index_ids(sort_by="create_time", sort_desc=False)
        assert index_ids.index(my_workflow_id_y) < index_ids.index(my_workflow_id_z)
        index_ids = self.workflow_populator.index_ids(sort_by="name")
        assert index_ids.index(my_workflow_id_y) < index_ids.index(my_workflow_id_z)
        index_ids = self.workflow_populator.index_ids(sort_by="name", sort_desc=False)
        assert index_ids.index(my_workflow_id_y) < index_ids.index(my_workflow_id_z)
        index_ids = self.workflow_populator.index_ids(sort_by="name", sort_desc=True)
        assert index_ids.index(my_workflow_id_z) < index_ids.index(my_workflow_id_y)

    def test_index_limit_and_offset(self):
        self.workflow_populator.simple_workflow("y_1")
        self.workflow_populator.simple_workflow("z_2")
        index_ids = self.workflow_populator.index_ids(limit=1)
        assert len(index_ids) == 1
        index_ids_offset = self.workflow_populator.index_ids(limit=1, offset=1)
        assert len(index_ids_offset) == 1
        assert index_ids[0] != index_ids_offset[0]

    def test_index_show_shared(self):
        my_workflow_id_1 = self.workflow_populator.simple_workflow("mine_1")
        my_email = self.dataset_populator.user_email()
        with self._different_user():
            their_workflow_id_1 = self.workflow_populator.simple_workflow("theirs_1")
            self.workflow_populator.share_with_user(their_workflow_id_1, my_email)
        index_ids = self.workflow_populator.index_ids()
        assert my_workflow_id_1 in index_ids
        assert their_workflow_id_1 in index_ids

        index_ids = self.workflow_populator.index_ids(show_shared=False)
        assert my_workflow_id_1 in index_ids
        assert their_workflow_id_1 not in index_ids

        index_ids = self.workflow_populator.index_ids(show_shared=True)
        assert my_workflow_id_1 in index_ids
        assert their_workflow_id_1 in index_ids

    def test_index_skip_step_counts(self):
        self.workflow_populator.simple_workflow("mine_1")
        index = self.workflow_populator.index()
        index_0 = index[0]
        assert "number_of_steps" in index_0
        assert index_0["number_of_steps"]
        index = self.workflow_populator.index(skip_step_counts=True)
        index_0 = index[0]
        assert "number_of_steps" not in index_0

    def test_index_search(self):
        name1, name2 = self.dataset_populator.get_random_name(), self.dataset_populator.get_random_name()
        workflow_id_1 = self.workflow_populator.simple_workflow(name1)
        self.workflow_populator.simple_workflow(name2)
        index_ids = self.workflow_populator.index_ids(search=name1)
        assert len(index_ids) == 1
        assert workflow_id_1 in index_ids

    def test_index_search_name(self):
        name1, name2 = self.dataset_populator.get_random_name(), self.dataset_populator.get_random_name()
        workflow_id_1 = self.workflow_populator.simple_workflow(name1)
        self.workflow_populator.simple_workflow(name2)
        self.workflow_populator.set_tags(workflow_id_1, [name2])
        index_ids = self.workflow_populator.index_ids(search=name2)
        # one found by tag and one found by name...
        assert len(index_ids) == 2
        assert workflow_id_1 in index_ids

        index_ids = self.workflow_populator.index_ids(search=f"name:{name2}")
        assert len(index_ids) == 1
        assert workflow_id_1 not in index_ids

    def test_index_search_name_exact_vs_inexact(self):
        name_prefix = self.dataset_populator.get_random_name()
        workflow_id_1 = self.workflow_populator.simple_workflow(name_prefix)
        longer_name = f"{name_prefix}_some_stuff_on_it"
        workflow_id_2 = self.workflow_populator.simple_workflow(longer_name)
        index_ids = self.workflow_populator.index_ids(search=f"name:{name_prefix}")
        assert len(index_ids) == 2
        assert workflow_id_1 in index_ids
        assert workflow_id_2 in index_ids

        # quoting it will ensure the name matches exactly.
        index_ids = self.workflow_populator.index_ids(search=f"name:'{name_prefix}'")
        assert len(index_ids) == 1
        assert workflow_id_1 in index_ids
        assert workflow_id_2 not in index_ids

    def test_index_search_tags(self):
        name1, name2 = self.dataset_populator.get_random_name(), self.dataset_populator.get_random_name()
        workflow_id_1 = self.workflow_populator.simple_workflow(name1)
        self.workflow_populator.simple_workflow(name2)
        moocowtag = f"moocowatag {uuid4()}"
        index_ids = self.workflow_populator.index_ids(search=moocowtag)
        assert len(index_ids) == 0
        self.workflow_populator.set_tags(workflow_id_1, [moocowtag, f"another{moocowtag}"])
        index_ids = self.workflow_populator.index_ids(search=moocowtag)
        assert workflow_id_1 in index_ids
        index_ids = self.workflow_populator.index_ids(search=f"tag:{moocowtag}")
        assert workflow_id_1 in index_ids

    def test_index_search_tags_multiple(self):
        name1 = self.dataset_populator.get_random_name()
        name2 = self.dataset_populator.get_random_name()
        name3 = self.dataset_populator.get_random_name()
        workflow_id_1 = self.workflow_populator.simple_workflow(name1)
        workflow_id_2 = self.workflow_populator.simple_workflow(name2)
        workflow_id_3 = self.workflow_populator.simple_workflow(name3)
        self.workflow_populator.set_tags(workflow_id_1, ["multipletagfilter1", "multipletagfilter2", "decoy1"])
        self.workflow_populator.set_tags(workflow_id_2, ["multipletagfilter1", "decoy2"])
        self.workflow_populator.set_tags(workflow_id_3, ["multipletagfilter2", "decoy3"])

        for search in ["multipletagfilter1", "tag:ipletagfilter1", "tag:'multipletagfilter1'"]:
            index_ids = self.workflow_populator.index_ids(search=search)
            assert workflow_id_1 in index_ids
            assert workflow_id_2 in index_ids
            assert workflow_id_3 not in index_ids

        for search in ["multipletagfilter2", "tag:ipletagfilter2", "tag:'multipletagfilter2'"]:
            index_ids = self.workflow_populator.index_ids(search=search)
            assert workflow_id_1 in index_ids
            assert workflow_id_2 not in index_ids
            assert workflow_id_3 in index_ids

        for search in [
            "multipletagfilter2 multipletagfilter1",
            "tag:filter2 tag:tagfilter1",
            "tag:'multipletagfilter2' tag:'multipletagfilter1'",
        ]:
            index_ids = self.workflow_populator.index_ids(search=search)
            assert workflow_id_1 in index_ids
            assert workflow_id_2 not in index_ids
            assert workflow_id_3 not in index_ids

    def test_search_casing(self):
        name1, name2 = (
            self.dataset_populator.get_random_name().upper(),
            self.dataset_populator.get_random_name().upper(),
        )
        workflow_id_1 = self.workflow_populator.simple_workflow(name1)
        self.workflow_populator.simple_workflow(name2)
        searchcasingtag = f"searchcasingtag{uuid4()}"
        self.workflow_populator.set_tags(workflow_id_1, [searchcasingtag, f"another{searchcasingtag}"])
        index_ids = self.workflow_populator.index_ids(search=name1.lower())
        assert len(index_ids) == 1
        assert workflow_id_1 in index_ids
        index_ids = self.workflow_populator.index_ids(search=searchcasingtag.upper())
        assert len(index_ids) == 1
        assert workflow_id_1 in index_ids

    def test_index_search_tags_exact(self):
        name1, name2 = self.dataset_populator.get_random_name(), self.dataset_populator.get_random_name()
        workflow_id_1 = self.workflow_populator.simple_workflow(name1)
        workflow_id_2 = self.workflow_populator.simple_workflow(name2)
        exact_tag_to_search = f"exacttagtosearch{uuid4()}"
        index_ids = self.workflow_populator.index_ids(search=exact_tag_to_search)
        assert len(index_ids) == 0
        self.workflow_populator.set_tags(workflow_id_1, [exact_tag_to_search])
        self.workflow_populator.set_tags(workflow_id_2, [f"{exact_tag_to_search}longer"])
        index_ids = self.workflow_populator.index_ids(search=exact_tag_to_search)
        assert workflow_id_1 in index_ids
        assert workflow_id_2 in index_ids
        index_ids = self.workflow_populator.index_ids(search=f"tag:{exact_tag_to_search}")
        assert workflow_id_1 in index_ids
        assert workflow_id_2 in index_ids
        index_ids = self.workflow_populator.index_ids(search=f"tag:'{exact_tag_to_search}'")
        assert workflow_id_1 in index_ids
        assert workflow_id_2 not in index_ids

    def test_index_published(self):
        # published workflows are also the default of what is displayed for anonymous API requests
        # this is tested in test_anonymous_published.
        uuid = str(uuid4())
        workflow_name = f"test_pubished_anon_{uuid}"
        with self._different_user():
            workflow_id = self.workflow_populator.simple_workflow(workflow_name, publish=True)

        assert workflow_id not in self.workflow_populator.index_ids()
        assert workflow_id in self.workflow_populator.index_ids(show_published=True)
        assert workflow_id not in self.workflow_populator.index_ids(show_published=False)

    def test_index_search_is_tags(self):
        my_workflow_id_1 = self.workflow_populator.simple_workflow("sitags_m_1")
        my_email = self.dataset_populator.user_email()
        with self._different_user():
            their_workflow_id_1 = self.workflow_populator.simple_workflow("sitags_shwm_1")
            self.workflow_populator.share_with_user(their_workflow_id_1, my_email)
            published_workflow_id_1 = self.workflow_populator.simple_workflow("sitags_p_1", publish=True)

        index_ids = self.workflow_populator.index_ids(search="is:published", show_published=True)
        assert published_workflow_id_1 in index_ids
        assert their_workflow_id_1 not in index_ids
        assert my_workflow_id_1 not in index_ids

        index_ids = self.workflow_populator.index_ids(search="is:shared_with_me")
        assert published_workflow_id_1 not in index_ids
        assert their_workflow_id_1 in index_ids
        assert my_workflow_id_1 not in index_ids

    def test_index_owner(self):
        my_workflow_id_1 = self.workflow_populator.simple_workflow("ownertags_m_1")
        email_1 = f"{uuid4()}@test.com"
        with self._different_user(email=email_1):
            published_workflow_id_1 = self.workflow_populator.simple_workflow("ownertags_p_1", publish=True)
            owner_1 = self._show_workflow(published_workflow_id_1)["owner"]

        email_2 = f"{uuid4()}@test.com"
        with self._different_user(email=email_2):
            published_workflow_id_2 = self.workflow_populator.simple_workflow("ownertags_p_2", publish=True)

        index_ids = self.workflow_populator.index_ids(search="is:published", show_published=True)
        assert published_workflow_id_1 in index_ids
        assert published_workflow_id_2 in index_ids
        assert my_workflow_id_1 not in index_ids

        index_ids = self.workflow_populator.index_ids(search=f"is:published u:{owner_1}", show_published=True)
        assert published_workflow_id_1 in index_ids
        assert published_workflow_id_2 not in index_ids
        assert my_workflow_id_1 not in index_ids

        index_ids = self.workflow_populator.index_ids(search=f"is:published u:'{owner_1}'", show_published=True)
        assert published_workflow_id_1 in index_ids
        assert published_workflow_id_2 not in index_ids
        assert my_workflow_id_1 not in index_ids

        index_ids = self.workflow_populator.index_ids(search=f"is:published {owner_1}", show_published=True)
        assert published_workflow_id_1 in index_ids
        assert published_workflow_id_2 not in index_ids
        assert my_workflow_id_1 not in index_ids

    def test_index_parameter_invalid_combinations(self):
        # these can all be called by themselves and return 200...
        response = self._get("workflows?show_hidden=true")
        self._assert_status_code_is(response, 200)
        response = self._get("workflows?show_deleted=true")
        self._assert_status_code_is(response, 200)
        response = self._get("workflows?show_shared=true")
        self._assert_status_code_is(response, 200)
        # but showing shared workflows along with deleted or hidden results in an error
        response = self._get("workflows?show_hidden=true&show_shared=true")
        self._assert_status_code_is(response, 400)
        self._assert_error_code_is(response, error_codes.error_codes_by_name["USER_REQUEST_INVALID_PARAMETER"])
        response = self._get("workflows?show_deleted=true&show_shared=true")
        self._assert_status_code_is(response, 400)
        self._assert_error_code_is(response, error_codes.error_codes_by_name["USER_REQUEST_INVALID_PARAMETER"])

    def test_index_total_matches(self):
        with self._different_user("isolated.wf.user@test.email"):
            my_workflow_id = self.workflow_populator.simple_workflow("mine_1")
            self.workflow_populator.simple_workflow("mine_2")
            my_email = self.dataset_populator.user_email()
            with self._different_user():
                their_shared_workflow_id = self.workflow_populator.simple_workflow("theirs_1")
                self.workflow_populator.share_with_user(their_shared_workflow_id, my_email)
                their_workflow_to_import_id = self.workflow_populator.simple_workflow("theirs_2", publish=True)
                self.workflow_populator.set_tags(their_workflow_to_import_id, ["theirs_2", "test"])

            import_response = self.__import_workflow(their_workflow_to_import_id)
            self._assert_status_code_is(import_response, 200)
            imported_wf_id = import_response.json()["id"]

            # add tags to my workflows
            self.workflow_populator.set_tags(my_workflow_id, ["mine_1", "test"])
            self.workflow_populator.set_tags(imported_wf_id, ["imported", "test"])

            # We should have 4 workflows now (2 mine, 1 shared with me, 1 imported)
            expected_number_of_workflows = 4
            workflows_response = self._get("workflows")
            self._assert_status_code_is(workflows_response, 200)
            assert workflows_response.headers["Total_matches"] == f"{expected_number_of_workflows}"
            workflows = workflows_response.json()
            assert len(workflows) == expected_number_of_workflows

    def test_upload(self):
        self.__test_upload(use_deprecated_route=False)

    def test_upload_deprecated(self):
        self.__test_upload(use_deprecated_route=True)

    def test_import_tools_requires_admin(self):
        response = self.__test_upload(import_tools=True, assert_ok=False)
        assert response.status_code == 403

    def __test_upload(
        self, use_deprecated_route=False, name="test_import", workflow=None, assert_ok=True, import_tools=False
    ):
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
            label = f"label_{order_index}"
            step_dict["label"] = label
            labels[order_index] = label

        def check_label_and_uuid(order_index, step_dict):
            assert order_index in uuids
            assert order_index in labels

            assert uuids[order_index] == step_dict["uuid"]
            assert labels[order_index] == step_dict["label"]

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
            assert step_dict["position"]["top"] != 1
            assert step_dict["position"]["left"] != 1
            step_dict["position"] = {"top": 1, "left": 1}

        map(tweak_step, steps.items())

        update(workflow_content)

        def check_step(step):
            order_index, step_dict = step
            check_label_and_uuid(order_index, step_dict)
            assert step_dict["position"]["top"] == 1
            assert step_dict["position"]["left"] == 1

        updated_workflow_content = self._download_workflow(workflow_id)
        map(check_step, updated_workflow_content["steps"].items())

        # Re-update against original workflow...
        update(original_workflow)

        updated_workflow_content = self._download_workflow(workflow_id)

        # Make sure the positions have been updated.
        map(tweak_step, updated_workflow_content["steps"].items())

    def test_update_tags(self):
        workflow_object = self.workflow_populator.load_workflow(name="test_import")
        workflow_id = self.__test_upload(workflow=workflow_object).json()["id"]
        update_payload = {}
        update_payload["tags"] = ["a_tag", "b_tag"]
        update_response = self._update_workflow(workflow_id, update_payload).json()
        assert update_response["tags"] == ["a_tag", "b_tag"]
        del update_payload["tags"]
        update_response = self._update_workflow(workflow_id, update_payload).json()
        assert update_response["tags"] == ["a_tag", "b_tag"]
        update_payload["tags"] = []
        update_response = self._update_workflow(workflow_id, update_payload).json()
        assert update_response["tags"] == []

    def test_update_name(self):
        original_name = "test update name"
        workflow_object = self.workflow_populator.load_workflow(name=original_name)
        workflow_object["license"] = "AAL"
        upload_response = self.__test_upload(workflow=workflow_object, name=original_name)
        workflow = upload_response.json()
        workflow_id = workflow["id"]
        assert workflow["name"] == original_name
        workflow_dict = self.workflow_populator.download_workflow(workflow_id)
        assert workflow_dict["license"] == "AAL"

        data = {"name": "my cool new name"}
        update_response = self._update_workflow(workflow["id"], data).json()
        assert update_response["name"] == "my cool new name"
        workflow_dict = self.workflow_populator.download_workflow(workflow_id)
        assert workflow_dict["license"] == "AAL"

    def test_update_name_for_workflow_with_subworkflows(self):
        workflow_id = self.workflow_populator.upload_yaml_workflow(
            """
class: GalaxyWorkflow
label: old name
inputs:
  dataset: data
steps:
  subworkflow:
    in:
      dataset: dataset
    outputs:
      output:
        outputSource: cat1/out_file1
    run:
      class: GalaxyWorkflow
      inputs:
        dataset:
          type: data
      steps:
        cat1:
          tool_id: cat1
          in:
            input1: dataset
  cat1:
    tool_id: cat1
    in:
      input1: subworkflow/output
"""
        )
        self.workflow_populator.download_workflow(workflow_id)
        new_name = "my cool new name"
        data = {"name": new_name}
        self._update_workflow(workflow_id, data).raise_for_status()
        post_update_workflow = self.workflow_populator.download_workflow(workflow_id)
        assert post_update_workflow["name"] == new_name

    def test_update_name_empty(self):
        # Update doesn't allow empty names.

        # Load a workflow with a given name.
        original_name = "test update name"
        workflow_object = self.workflow_populator.load_workflow(name=original_name)
        upload_response = self.__test_upload(workflow=workflow_object, name=original_name)
        workflow = upload_response.json()
        assert workflow["name"] == original_name

        # Try to update the name to an empty string (also change steps to force an update).
        data = {"name": "", "steps": {}}
        update_response = self._update_workflow(workflow["id"], data)
        assert update_response.json()["err_msg"] == "Workflow must have a valid name"
        self._assert_status_code_is(update_response, 400)
        workflow_dict = self.workflow_populator.download_workflow(workflow["id"])
        assert workflow_dict["name"] == original_name

    @skip_without_tool("select_from_dataset_in_conditional")
    def test_workflow_run_form_with_broken_dataset(self):
        workflow_id = self.workflow_populator.upload_yaml_workflow(
            """
class: GalaxyWorkflow
inputs:
  dataset: data
steps:
  select_from_dataset_in_conditional:
    tool_id: select_from_dataset_in_conditional
    in:
      single: dataset
    state:
      cond:
        cond: single
        select_single: abc
        inner_cond:
          inner_cond: single
          select_single: abc
"""
        )
        with self.dataset_populator.test_history() as history_id:
            self.dataset_populator.new_dataset(history_id, content="a", file_type="tabular", wait=True)
            workflow = self._download_workflow(workflow_id, style="run", history_id=history_id)
            assert not workflow["has_upgrade_messages"]
            assert workflow["steps"][1]["inputs"][0]["value"] == {"__class__": "ConnectedValue"}

    def test_refactor(self):
        workflow_id = self.workflow_populator.upload_yaml_workflow(
            """
class: GalaxyWorkflow
inputs:
  test_input: data
steps:
  first_cat:
    tool_id: cat
    in:
      input1: test_input
"""
        )
        actions = [
            {"action_type": "update_step_label", "step": {"order_index": 0}, "label": "new_label"},
        ]
        # perform refactoring as dry run
        refactor_response = self.workflow_populator.refactor_workflow(workflow_id, actions, dry_run=True)
        refactor_response.raise_for_status()
        assert refactor_response.json()["workflow"]["steps"]["0"]["label"] == "new_label"

        # perform refactoring as dry run but specify editor style response
        refactor_response = self.workflow_populator.refactor_workflow(
            workflow_id, actions, dry_run=True, style="editor"
        )
        refactor_response.raise_for_status()
        assert refactor_response.json()["workflow"]["steps"]["0"]["label"] == "new_label"

        # download the original workflow and make sure the dry run didn't modify that label
        workflow_dict = self.workflow_populator.download_workflow(workflow_id)
        assert workflow_dict["steps"]["0"]["label"] == "test_input"

        refactor_response = self.workflow_populator.refactor_workflow(workflow_id, actions)
        refactor_response.raise_for_status()
        assert refactor_response.json()["workflow"]["steps"]["0"]["label"] == "new_label"

        # this time dry_run was default of False, so the label is indeed changed
        workflow_dict = self.workflow_populator.download_workflow(workflow_id)
        assert workflow_dict["steps"]["0"]["label"] == "new_label"

    def test_refactor_tool_state_upgrade(self):
        workflow_id = self.workflow_populator.upload_yaml_workflow(
            """
class: GalaxyWorkflow
inputs: {}
steps:
  multiple_versions_changes:
    tool_id: multiple_versions_changes
    tool_version: "0.1"
    state:
      inttest: 1
      cond:
        bool_to_select: false
"""
        )
        actions = [{"action_type": "upgrade_all_steps"}]
        refactor_response = self.workflow_populator.refactor_workflow(workflow_id, actions, dry_run=True)
        refactor_response.raise_for_status()
        refactor_result = refactor_response.json()
        upgrade_result = refactor_result["action_executions"][0]
        assert upgrade_result["action"]["action_type"] == "upgrade_all_steps"
        message_one, message_two = upgrade_result["messages"]
        assert message_one["message"] == "No value found for 'floattest'. Using default: '1.0'."
        assert message_one["input_name"] == "floattest"
        assert message_two["message"] == "The selected case is unavailable/invalid. Using default: 'b'."
        assert message_two["input_name"] == "cond|bool_to_select"

        refactor_response = self.workflow_populator.refactor_workflow(workflow_id, actions, dry_run=False)
        refactor_response.raise_for_status()

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

    def test_import_export_dynamic(self):
        workflow_id = self._upload_yaml_workflow(
            """
class: GalaxyWorkflow
steps:
  - type: input
    label: input1
  - tool_id: cat1
    label: first_cat
    state:
      input1:
        $link: 0
  - label: embed1
    run:
      class: GalaxyTool
      command: echo 'hello world 2' > $output1
      outputs:
        output1:
          format: txt
  - tool_id: cat1
    state:
      input1:
        $link: first_cat/out_file1
      queries:
        input2:
          $link: embed1/output1
test_data:
  input1: "hello world"
"""
        )
        downloaded_workflow = self._download_workflow(workflow_id)
        # The _upload_yaml_workflow entry point uses an admin key, but if we try to
        # do the raw re-import as a regular user we expect a 403 error.
        response = self.workflow_populator.create_workflow_response(downloaded_workflow)
        self._assert_status_code_is(response, 403)

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
            step_annotations = {step["annotation"] for step in imported_workflow["steps"].values()}
            assert "input1 description" in step_annotations

    def test_import_subworkflows(self):
        def get_subworkflow_content_id(workflow_id):
            workflow_contents = self._download_workflow(workflow_id, style="editor")
            steps = workflow_contents["steps"]
            subworkflow_step = next(s for s in steps.values() if s["type"] == "subworkflow")
            return subworkflow_step["content_id"]

        workflow_id = self._upload_yaml_workflow(WORKFLOW_NESTED_SIMPLE, publish=True)
        subworkflow_content_id = get_subworkflow_content_id(workflow_id)
        instance_response = self._get(f"workflows/{subworkflow_content_id}?instance=true")
        self._assert_status_code_is(instance_response, 200)
        subworkflow = instance_response.json()
        assert subworkflow["inputs"]["0"]["label"] == "inner_input"
        assert subworkflow["name"] == "Workflow"
        assert subworkflow["hidden"]
        with self._different_user():
            other_import_response = self.__import_workflow(workflow_id)
            self._assert_status_code_is(other_import_response, 200)
            imported_workflow_id = other_import_response.json()["id"]
            imported_subworkflow_content_id = get_subworkflow_content_id(imported_workflow_id)
            assert subworkflow_content_id != imported_subworkflow_content_id

    def test_subworkflow_inputs_optional_editor(self):
        workflow_id = self._upload_yaml_workflow(
            """
class: GalaxyWorkflow
steps:
  nested_workflow:
    run:
      class: GalaxyWorkflow
      inputs:
        - id: inner_input
          optional: true
      outputs:
        - outputSource: inner_input/output
      steps: []
"""
        )
        workflow_contents = self._download_workflow(workflow_id, style="editor")
        assert workflow_contents["steps"]["0"]["inputs"][0]["optional"]

    def test_not_importable_prevents_import(self):
        workflow_id = self.workflow_populator.simple_workflow("test_not_importportable")
        with self._different_user():
            other_import_response = self.__import_workflow(workflow_id)
            self._assert_status_code_is(other_import_response, 403)

    def test_url_import(self):
        url = "https://raw.githubusercontent.com/galaxyproject/galaxy/release_19.09/test/base/data/test_workflow_1.ga"
        workflow_id = self._post("workflows", data={"archive_source": url}).json()["id"]
        workflow = self._download_workflow(workflow_id)
        assert "TestWorkflow1" in workflow["name"]
        assert (
            workflow.get("source_metadata").get("url") == url
        )  # disappearance of source_metadata on modification is tested in test_trs_import

    def test_base64_import(self):
        base64_url = "base64://" + base64.b64encode(workflow_str.encode("utf-8")).decode("utf-8")
        response = self._post("workflows", data={"archive_source": base64_url})
        response.raise_for_status()
        workflow_id = response.json()["id"]
        workflow = self._download_workflow(workflow_id)
        assert "TestWorkflow1" in workflow["name"]

    def test_trs_import(self):
        trs_payload = {
            "archive_source": "trs_tool",
            "trs_server": "dockstore",
            "trs_tool_id": "#workflow/github.com/jmchilton/galaxy-workflow-dockstore-example-1/mycoolworkflow",
            "trs_version_id": "master",
        }
        workflow_id = self._post("workflows", data=trs_payload).json()["id"]
        original_workflow = self._download_workflow(workflow_id)
        assert "Test Workflow" in original_workflow["name"]
        assert original_workflow.get("source_metadata").get("trs_tool_id") == trs_payload["trs_tool_id"]
        assert original_workflow.get("source_metadata").get("trs_version_id") == trs_payload["trs_version_id"]
        assert original_workflow.get("source_metadata").get("trs_server") == "dockstore"

        # refactor workflow and check that the trs id is removed
        actions = [
            {"action_type": "update_step_label", "step": {"order_index": 0}, "label": "new_label"},
        ]
        self.workflow_populator.refactor_workflow(workflow_id, actions)
        refactored_workflow = self._download_workflow(workflow_id)
        assert refactored_workflow.get("source_metadata") is None

        # reupload original_workflow and check that the trs id is removed
        reuploaded_workflow_id = self.workflow_populator.create_workflow(original_workflow)
        reuploaded_workflow = self._download_workflow(reuploaded_workflow_id)
        assert reuploaded_workflow.get("source_metadata") is None

    def test_trs_import_from_dockstore_trs_url(self):
        trs_payload = {
            "archive_source": "trs_tool",
            "trs_url": "https://dockstore.org/api/ga4gh/trs/v2/tools/"
            "%23workflow%2Fgithub.com%2Fjmchilton%2Fgalaxy-workflow-dockstore-example-1%2Fmycoolworkflow/"
            "versions/master",
        }
        workflow_id = self._post("workflows", data=trs_payload).json()["id"]
        original_workflow = self._download_workflow(workflow_id)
        assert "Test Workflow" in original_workflow["name"]
        assert (
            original_workflow.get("source_metadata").get("trs_tool_id")
            == "#workflow/github.com/jmchilton/galaxy-workflow-dockstore-example-1/mycoolworkflow"
        )
        assert original_workflow.get("source_metadata").get("trs_version_id") == "master"
        assert not original_workflow.get("source_metadata").get("trs_server")
        assert original_workflow.get("source_metadata").get("trs_url") == (
            "https://dockstore.org/api/ga4gh/trs/v2/tools/"
            "%23workflow%2Fgithub.com%2Fjmchilton%2Fgalaxy-workflow-dockstore-example-1%2Fmycoolworkflow/"
            "versions/master"
        )

        # refactor workflow and check that the trs id is removed
        actions = [
            {"action_type": "update_step_label", "step": {"order_index": 0}, "label": "new_label"},
        ]
        self.workflow_populator.refactor_workflow(workflow_id, actions)
        refactored_workflow = self._download_workflow(workflow_id)
        assert refactored_workflow.get("source_metadata") is None

        # reupload original_workflow and check that the trs id is removed
        reuploaded_workflow_id = self.workflow_populator.create_workflow(original_workflow)
        reuploaded_workflow = self._download_workflow(reuploaded_workflow_id)
        assert reuploaded_workflow.get("source_metadata") is None

    def test_trs_import_from_workflowhub_trs_url(self):
        trs_payload = {
            "archive_source": "trs_tool",
            "trs_url": "https://workflowhub.eu/ga4gh/trs/v2/tools/109/versions/5",
        }
        workflow_id = self._post("workflows", data=trs_payload).json()["id"]
        original_workflow = self._download_workflow(workflow_id)
        assert "COVID-19: variation analysis reporting" in original_workflow["name"]
        assert original_workflow.get("source_metadata").get("trs_tool_id") == "109"
        assert original_workflow.get("source_metadata").get("trs_version_id") == "5"
        assert not original_workflow.get("source_metadata").get("trs_server")
        assert (
            original_workflow.get("source_metadata").get("trs_url")
            == "https://workflowhub.eu/ga4gh/trs/v2/tools/109/versions/5"
        )

        # refactor workflow and check that the trs id is removed
        actions = [
            {"action_type": "update_step_label", "step": {"order_index": 0}, "label": "new_label"},
        ]
        self.workflow_populator.refactor_workflow(workflow_id, actions)
        refactored_workflow = self._download_workflow(workflow_id)
        assert refactored_workflow.get("source_metadata") is None

        # reupload original_workflow and check that the trs id is removed
        reuploaded_workflow_id = self.workflow_populator.create_workflow(original_workflow)
        reuploaded_workflow = self._download_workflow(reuploaded_workflow_id)
        assert reuploaded_workflow.get("source_metadata") is None

    def test_anonymous_published(self):
        def anonymous_published_workflows(explicit_query_parameter):
            if explicit_query_parameter:
                index_url = "workflows?show_published=True"
            else:
                index_url = "workflows"
            workflows_url = self._api_url(index_url)
            response = get(workflows_url)
            response.raise_for_status()
            return response.json()

        workflow_name = f"test published example {uuid4()}"
        names = [w["name"] for w in anonymous_published_workflows(True)]
        assert workflow_name not in names
        workflow_id = self.workflow_populator.simple_workflow(workflow_name, publish=True)

        for explicit_query_parameter in [True, False]:
            workflow_index = anonymous_published_workflows(explicit_query_parameter)
            names = [w["name"] for w in workflow_index]
            assert workflow_name in names
            ids = [w["id"] for w in workflow_index]
            assert workflow_id in ids

    def test_import_published(self):
        workflow_id = self.workflow_populator.simple_workflow("test_import_published", publish=True)
        with self._different_user():
            other_import_response = self.__import_workflow(workflow_id, deprecated_route=True)
            self._assert_status_code_is(other_import_response, 200)
            self._assert_user_has_workflow_with_name("imported: test_import_published")

    def test_import_published_api(self):
        workflow_id = self.workflow_populator.simple_workflow("test_import_published", publish=True)
        with self._different_user():
            other_import_response = self.__import_workflow(workflow_id, deprecated_route=False)
            self._assert_status_code_is(other_import_response, 200)
            workflow = self._download_workflow(other_import_response.json()["id"])
            assert workflow["steps"]["2"]["tool_version"] == "1.0.0"

    def test_export(self):
        uploaded_workflow_id = self.workflow_populator.simple_workflow("test_for_export")
        downloaded_workflow = self._download_workflow(uploaded_workflow_id)
        assert downloaded_workflow["name"] == "test_for_export"
        steps = downloaded_workflow["steps"]
        assert len(steps) == 3
        assert "0" in steps
        first_step = steps["0"]
        self._assert_has_keys(first_step, "inputs", "outputs")
        inputs = first_step["inputs"]
        assert len(inputs) > 0, first_step
        first_input = inputs[0]
        assert first_input["name"] == "WorkflowInput1"
        assert first_input["description"] == "input1 description"
        self._assert_has_keys(downloaded_workflow, "a_galaxy_workflow", "format-version", "annotation", "uuid", "steps")
        for step in downloaded_workflow["steps"].values():
            self._assert_has_keys(
                step,
                "id",
                "type",
                "tool_id",
                "tool_version",
                "name",
                "tool_state",
                "annotation",
                "inputs",
                "workflow_outputs",
                "outputs",
            )
            if step["type"] == "tool":
                self._assert_has_keys(step, "post_job_actions")

    def test_export_format2(self):
        uploaded_workflow_id = self.workflow_populator.simple_workflow("test_for_export_format2")
        downloaded_workflow = self._download_workflow(uploaded_workflow_id, style="format2")
        assert downloaded_workflow["class"] == "GalaxyWorkflow"

    def test_export_editor(self):
        uploaded_workflow_id = self.workflow_populator.simple_workflow("test_for_export")
        downloaded_workflow = self._download_workflow(uploaded_workflow_id, style="editor")
        self._assert_has_keys(downloaded_workflow, "name", "steps", "upgrade_messages")
        for step in downloaded_workflow["steps"].values():
            self._assert_has_keys(
                step,
                "id",
                "type",
                "content_id",
                "name",
                "tool_state",
                "tooltip",
                "inputs",
                "outputs",
                "config_form",
                "annotation",
                "post_job_actions",
                "workflow_outputs",
                "uuid",
                "label",
            )

    @skip_without_tool("output_filter_with_input")
    def test_export_editor_filtered_outputs(self):
        template = """
class: GalaxyWorkflow
steps:
  - tool_id: output_filter_with_input
    state:
      produce_out_1: {produce_out_1}
      filter_text_1: {filter_text_1}
      produce_collection: false
      produce_paired_collection: false
"""
        workflow_id = self._upload_yaml_workflow(template.format(produce_out_1="false", filter_text_1="false"))
        downloaded_workflow = self._download_workflow(workflow_id, style="editor")
        outputs = downloaded_workflow["steps"]["0"]["outputs"]
        assert len(outputs) == 1
        assert outputs[0]["name"] == "out_3"
        workflow_id = self._upload_yaml_workflow(template.format(produce_out_1="true", filter_text_1="false"))
        downloaded_workflow = self._download_workflow(workflow_id, style="editor")
        outputs = downloaded_workflow["steps"]["0"]["outputs"]
        assert len(outputs) == 2
        assert outputs[0]["name"] == "out_1"
        assert outputs[1]["name"] == "out_3"
        workflow_id = self._upload_yaml_workflow(template.format(produce_out_1="true", filter_text_1="foo"))
        downloaded_workflow = self._download_workflow(workflow_id, style="editor")
        outputs = downloaded_workflow["steps"]["0"]["outputs"]
        assert len(outputs) == 3
        assert outputs[0]["name"] == "out_1"
        assert outputs[1]["name"] == "out_2"
        assert outputs[2]["name"] == "out_3"

    @skip_without_tool("output_filter_exception_1")
    def test_export_editor_filtered_outputs_exception_handling(self):
        workflow_id = self._upload_yaml_workflow(
            """
class: GalaxyWorkflow
steps:
  - tool_id: output_filter_exception_1
"""
        )
        downloaded_workflow = self._download_workflow(workflow_id, style="editor")
        outputs = downloaded_workflow["steps"]["0"]["outputs"]
        assert len(outputs) == 2
        assert outputs[0]["name"] == "out_1"
        assert outputs[1]["name"] == "out_2"

    @skip_without_tool("collection_type_source")
    def test_export_editor_collection_type_source(self):
        workflow_id = self._upload_yaml_workflow(
            """
class: GalaxyWorkflow
inputs:
  - id: text_input1
    type: collection
    collection_type: "list:paired"
steps:
  - tool_id: collection_type_source
    in:
      input_collect: text_input1
"""
        )
        downloaded_workflow = self._download_workflow(workflow_id, style="editor")
        steps = downloaded_workflow["steps"]
        assert len(steps) == 2
        # Non-subworkflow collection_type_source tools will be handled by the client,
        # so collection_type should be None here.
        assert steps["1"]["outputs"][0]["collection_type"] is None

    @skip_without_tool("collection_type_source")
    def test_export_editor_subworkflow_collection_type_source(self):
        workflow_id = self._upload_yaml_workflow(
            """
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
"""
        )
        downloaded_workflow = self._download_workflow(workflow_id, style="editor")
        steps = downloaded_workflow["steps"]
        assert len(steps) == 2
        assert steps["1"]["type"] == "subworkflow"
        assert steps["1"]["outputs"][0]["collection_type"] == "list:paired"

    def test_import_missing_tool(self):
        workflow = self.workflow_populator.load_workflow_from_resource(name="test_workflow_missing_tool")
        workflow_id = self.workflow_populator.create_workflow(workflow)
        workflow_description = self._show_workflow(workflow_id)
        steps = workflow_description["steps"]
        missing_tool_steps = [v for v in steps.values() if v["tool_id"] == "cat_missing_tool"]
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
        self.__run_cat_workflow(inputs_by="step_index")

    @skip_without_tool("cat1")
    def test_run_workflow_by_uuid(self):
        self.__run_cat_workflow(inputs_by="step_uuid")

    @skip_without_tool("cat1")
    def test_run_workflow_by_uuid_implicitly(self):
        self.__run_cat_workflow(inputs_by="uuid_implicitly")

    @skip_without_tool("cat1")
    def test_run_workflow_by_name(self):
        self.__run_cat_workflow(inputs_by="name")

    @skip_without_tool("cat1")
    def test_run_workflow(self):
        self.__run_cat_workflow(inputs_by="step_id")

    @skip_without_tool("cat1")
    def test_run_workflow_by_deferred_url(self):
        with self.dataset_populator.test_history() as history_id:
            self.__run_cat_workflow(inputs_by="deferred_url", history_id=history_id)
            # it did an upload of the inputs anyway - so this is a 3 is a bit of a hack...
            # TODO fix this.
            input_dataset_details = self.dataset_populator.get_history_dataset_details(history_id, hid=3)
            assert input_dataset_details["state"] == "deferred"

    @skip_without_tool("cat1")
    def test_run_workflow_by_url(self):
        with self.dataset_populator.test_history() as history_id:
            self.__run_cat_workflow(inputs_by="url", history_id=history_id)
            input_dataset_details = self.dataset_populator.get_history_dataset_details(
                history_id, hid=3, assert_ok=False
            )
            assert input_dataset_details["state"] == "ok"

    @skip_without_tool("cat1")
    def test_run_workflow_with_valid_url_hashes(self):
        with self.dataset_populator.test_history() as history_id:
            workflow = self.workflow_populator.load_workflow(name="test_for_run_invalid_url_hashes")
            workflow_id = self.workflow_populator.create_workflow(workflow)
            input_b64_1 = base64.b64encode(b"1 2 3").decode("utf-8")
            input_b64_2 = base64.b64encode(b"4 5 6").decode("utf-8")
            deferred = False
            hashes_1 = [{"hash_function": "MD5", "hash_value": "5ba48b6e5a7c4d4930fda256f411e55b"}]
            hashes_2 = [{"hash_function": "MD5", "hash_value": "ad0f811416f7ed2deb9122007d649fb0"}]
            inputs = {
                "WorkflowInput1": {
                    "src": "url",
                    "url": f"base64://{input_b64_1}",
                    "ext": "txt",
                    "deferred": deferred,
                    "hashes": hashes_1,
                },
                "WorkflowInput2": {
                    "src": "url",
                    "url": f"base64://{input_b64_2}",
                    "ext": "txt",
                    "deferred": deferred,
                    "hashes": hashes_2,
                },
            }
            workflow_request = dict(
                history=f"hist_id={history_id}",
            )
            workflow_request["inputs"] = json.dumps(inputs)
            workflow_request["inputs_by"] = "name"
            invocation_id = self.workflow_populator.invoke_workflow_and_wait(
                workflow_id, request=workflow_request
            ).json()["id"]
            invocation = self._invocation_details(workflow_id, invocation_id)
            assert invocation["state"] == "scheduled", invocation
            invocation_jobs = self.workflow_populator.get_invocation_jobs(invocation_id)
            for job in invocation_jobs:
                assert job["state"] == "ok"

    @skip_without_tool("cat1")
    def test_run_workflow_with_invalid_url_hashes(self):
        with self.dataset_populator.test_history() as history_id:
            workflow = self.workflow_populator.load_workflow(name="test_for_run_invalid_url_hashes")
            workflow_id = self.workflow_populator.create_workflow(workflow)
            input_b64_1 = base64.b64encode(b"1 2 3").decode("utf-8")
            input_b64_2 = base64.b64encode(b"4 5 6").decode("utf-8")
            deferred = False
            hashes = [{"hash_function": "MD5", "hash_value": "abadmd5sumhash"}]
            inputs = {
                "WorkflowInput1": {
                    "src": "url",
                    "url": f"base64://{input_b64_1}",
                    "ext": "txt",
                    "deferred": deferred,
                    "hashes": hashes,
                },
                "WorkflowInput2": {
                    "src": "url",
                    "url": f"base64://{input_b64_2}",
                    "ext": "txt",
                    "deferred": deferred,
                    "hashes": hashes,
                },
            }
            workflow_request = dict(
                history=f"hist_id={history_id}",
            )
            workflow_request["inputs"] = json.dumps(inputs)
            workflow_request["inputs_by"] = "name"
            invocation_id = self.workflow_populator.invoke_workflow_and_wait(
                workflow_id, request=workflow_request, assert_ok=False
            ).json()["id"]
            invocation_details = self._invocation_details(workflow_id, invocation_id)
            assert invocation_details["state"] == "failed"
            assert len(invocation_details["messages"]) == 1
            message = invocation_details["messages"][0]
            assert message["reason"] == "dataset_failed"

    @skip_without_tool("cat1")
    def test_run_workflow_with_invalid_url(self):
        with self.dataset_populator.test_history() as history_id:
            workflow = self.workflow_populator.load_workflow(name="test_for_run_invalid_url")
            workflow_id = self.workflow_populator.create_workflow(workflow)
            deferred = False
            inputs = {
                "WorkflowInput1": {
                    "src": "url",
                    "url": "gxfiles://thisurl/doesnt/work",
                    "ext": "txt",
                    "deferred": deferred,
                },
                "WorkflowInput2": {
                    "src": "url",
                    "url": "gxfiles://thisurl/doesnt/work",
                    "ext": "txt",
                    "deferred": deferred,
                },
            }
            workflow_request = dict(
                history=f"hist_id={history_id}",
            )
            workflow_request["inputs"] = json.dumps(inputs)
            workflow_request["inputs_by"] = "name"
            invocation_id = self.workflow_populator.invoke_workflow_and_wait(
                workflow_id, request=workflow_request, assert_ok=False
            ).json()["id"]
            invocation_details = self._invocation_details(workflow_id, invocation_id)
            assert invocation_details["state"] == "failed"
            assert len(invocation_details["messages"]) == 1
            message = invocation_details["messages"][0]
            assert message["reason"] == "dataset_failed"

    def __run_cat_workflow(self, inputs_by, history_id: Optional[str] = None):
        workflow = self.workflow_populator.load_workflow(name="test_for_run")
        workflow["steps"]["0"]["uuid"] = str(uuid4())
        workflow["steps"]["1"]["uuid"] = str(uuid4())
        workflow_request, _, workflow_id = self._setup_workflow_run(
            workflow, inputs_by=inputs_by, history_id=history_id
        )
        invocation_id = self.workflow_populator.invoke_workflow_and_wait(workflow_id, request=workflow_request).json()[
            "id"
        ]
        invocation = self._invocation_details(workflow_id, invocation_id)
        assert invocation["state"] == "scheduled", invocation

    @skip_without_tool("collection_creates_pair")
    def test_workflow_run_output_collections(self) -> None:
        with self.dataset_populator.test_history() as history_id:
            self._run_workflow(WORKFLOW_WITH_OUTPUT_COLLECTION, history_id=history_id)
            assert "a\nc\nb\nd\n" == self.dataset_populator.get_history_dataset_content(history_id, hid=0)

    @skip_without_tool("job_properties")
    @skip_without_tool("identifier_multiple_in_conditional")
    def test_workflow_resume_from_failed_step(self):
        workflow_id = self._upload_yaml_workflow(
            """
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
            $link: 0/out_file1
    thedata: null
  cat:
    tool_id: cat1
    in:
      input1: identifier/output1
      queries_0|input2: identifier/output1
"""
        )
        with self.dataset_populator.test_history() as history_id:
            invocation_response = self.workflow_populator.invoke_workflow(workflow_id, history_id=history_id)
            invocation_id = invocation_response.json()["id"]
            self.workflow_populator.wait_for_workflow(workflow_id, invocation_id, history_id, assert_ok=False)
            failed_dataset_one = self.dataset_populator.get_history_dataset_details(
                history_id, hid=1, wait=True, assert_ok=False
            )
            assert failed_dataset_one["state"] == "error", failed_dataset_one
            paused_dataset = self.dataset_populator.get_history_dataset_details(
                history_id, hid=5, wait=True, assert_ok=False
            )
            assert paused_dataset["state"] == "paused", paused_dataset
            inputs = {"thebool": "false", "failbool": "false", "rerun_remap_job_id": failed_dataset_one["creating_job"]}
            self.dataset_populator.run_tool(
                tool_id="job_properties",
                inputs=inputs,
                history_id=history_id,
            )
            unpaused_dataset_1 = self.dataset_populator.get_history_dataset_details(
                history_id, hid=5, wait=True, assert_ok=False
            )
            assert unpaused_dataset_1["state"] == "ok"
            self.dataset_populator.wait_for_history(history_id, assert_ok=False)
            unpaused_dataset_2 = self.dataset_populator.get_history_dataset_details(
                history_id, hid=6, wait=True, assert_ok=False
            )
            assert unpaused_dataset_2["state"] == "ok"

    @skip_without_tool("job_properties")
    @skip_without_tool("collection_creates_list")
    def test_workflow_resume_from_failed_step_with_hdca_input(self):
        workflow_id = self._upload_yaml_workflow(
            """
class: GalaxyWorkflow
steps:
  job_props:
    tool_id: job_properties
    state:
      thebool: true
      failbool: true
  list_in_list_out:
    tool_id: collection_creates_list
    in:
      input1: job_props/list_output
  identifier:
    tool_id: identifier_collection
    in:
      input1: list_in_list_out/list_output
"""
        )
        with self.dataset_populator.test_history() as history_id:
            invocation_id = self.__invoke_workflow(workflow_id, history_id=history_id)
            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id, workflow_id, invocation_id, assert_ok=False
            )
            failed_dataset_one = self.dataset_populator.get_history_dataset_details(
                history_id, hid=1, wait=True, assert_ok=False
            )
            assert failed_dataset_one["state"] == "error", failed_dataset_one
            paused_colletion = self.dataset_populator.get_history_collection_details(
                history_id, hid=7, wait=True, assert_ok=False
            )
            first_paused_element = paused_colletion["elements"][0]["object"]
            assert first_paused_element["state"] == "paused", first_paused_element
            dependent_dataset = self.dataset_populator.get_history_dataset_details(
                history_id, hid=8, wait=True, assert_ok=False
            )
            assert dependent_dataset["state"] == "paused"
            inputs = {"thebool": "false", "failbool": "false", "rerun_remap_job_id": failed_dataset_one["creating_job"]}
            self.dataset_populator.run_tool(
                tool_id="job_properties",
                inputs=inputs,
                history_id=history_id,
            )
            paused_colletion = self.dataset_populator.get_history_collection_details(
                history_id, hid=7, wait=True, assert_ok=False
            )
            first_paused_element = paused_colletion["elements"][0]["object"]
            assert first_paused_element["state"] == "ok"
            self.dataset_populator.wait_for_history(history_id, assert_ok=False)
            dependent_dataset = self.dataset_populator.get_history_dataset_details(
                history_id, hid=8, wait=True, assert_ok=False
            )
            assert dependent_dataset["name"].startswith("identifier_collection")
            assert dependent_dataset["state"] == "ok"

    @skip_without_tool("fail_identifier")
    @skip_without_tool("identifier_collection")
    def test_workflow_resume_with_mapped_over_input(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_workflow(
                """
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
    collection_type: list
    elements:
      - identifier: fail
        value: 1.fastq
        type: File
      - identifier: success
        value: 1.fastq
        type: File
""",
                history_id=history_id,
                assert_ok=False,
                wait=True,
            )
            history_contents = self.dataset_populator._get_contents_request(history_id=history_id).json()
            input_collection = self.dataset_populator.get_history_collection_details(history_id, hid=1, assert_ok=False)
            first_input = input_collection["elements"][0]
            paused_dataset = history_contents[-1]
            failed_dataset = self.dataset_populator.get_history_dataset_details(history_id, hid=5, assert_ok=False)
            assert paused_dataset["state"] == "paused", paused_dataset
            assert failed_dataset["state"] == "error", failed_dataset
            inputs = {
                "input1": {"values": [{"src": "dce", "id": first_input["id"]}]},
                "failbool": "false",
                "rerun_remap_job_id": failed_dataset["creating_job"],
            }
            run_dict = self.dataset_populator.run_tool(
                tool_id="fail_identifier",
                inputs=inputs,
                history_id=history_id,
            )
            unpaused_dataset = self.dataset_populator.get_history_dataset_details(
                history_id, wait=True, assert_ok=False
            )
            assert unpaused_dataset["state"] == "ok"
            contents = self.dataset_populator.get_history_dataset_content(history_id, hid=7, assert_ok=False)
            assert contents == "fail\nsuccess\n", contents
            replaced_hda_id = run_dict["outputs"][0]["id"]
            replaced_hda = self.dataset_populator.get_history_dataset_details(
                history_id, dataset_id=replaced_hda_id, wait=True, assert_ok=False
            )
            assert not replaced_hda["visible"], replaced_hda

    def test_workflow_resume_with_mapped_over_collection_input(self):
        # Test that replacement and resume also works if the failed job re-run works on a input DCE
        with self.dataset_populator.test_history() as history_id:
            job_summary = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input_collection: collection
steps:
- tool_id: collection_creates_list_of_pairs
  state:
    failbool: true
  in:
    input1:
      source: input_collection
- tool_id: collection_creates_list_of_pairs
  state:
    failbool: false
  in:
    input1:
      source: 1/list_output
test_data:
  input_collection:
    collection_type: "list:list:paired"
""",
                history_id=history_id,
                assert_ok=False,
                wait=True,
            )
            invocation = self.workflow_populator.get_invocation(job_summary.invocation_id, step_details=True)
            failed_step = invocation["steps"][1]
            assert failed_step["jobs"][0]["state"] == "error"
            failed_hdca_id = failed_step["output_collections"]["list_output"]["id"]
            failed_hdca = self.dataset_populator.get_history_collection_details(
                history_id=history_id, content_id=failed_hdca_id, assert_ok=False
            )
            assert (
                failed_hdca["elements"][0]["object"]["elements"][0]["object"]["elements"][0]["object"]["state"]
                == "error"
            )
            paused_step = invocation["steps"][2]
            # job not created, input in error state
            assert paused_step["jobs"][0]["state"] == "paused"
            input_hdca = self.dataset_populator.get_history_collection_details(
                history_id=history_id, content_id=job_summary.inputs["input_collection"]["id"], assert_ok=False
            )
            # now re-run errored job
            inputs = {
                "input1": {"values": [{"src": "dce", "id": input_hdca["elements"][0]["id"]}]},
                "failbool": "false",
                "rerun_remap_job_id": failed_step["jobs"][0]["id"],
            }
            run_response = self.dataset_populator.run_tool(
                tool_id="collection_creates_list_of_pairs",
                inputs=inputs,
                history_id=history_id,
            )
            assert not run_response["output_collections"][0]["visible"]
            self.dataset_populator.wait_for_job(paused_step["jobs"][0]["id"])
            invocation = self.workflow_populator.get_invocation(job_summary.invocation_id, step_details=True)
            rerun_step = invocation["steps"][1]
            assert rerun_step["jobs"][0]["state"] == "ok"
            replaced_hdca = self.dataset_populator.get_history_collection_details(
                history_id=history_id, content_id=failed_hdca_id, assert_ok=False
            )
            assert (
                replaced_hdca["elements"][0]["object"]["elements"][0]["object"]["elements"][0]["object"]["state"]
                == "ok"
            )

    @skip_without_tool("multi_data_optional")
    def test_workflow_list_list_multi_data_map_over(self):
        # Test that a list:list is reduced to list with a multiple="true" data input
        workflow_id = self._upload_yaml_workflow(
            """
class: GalaxyWorkflow
inputs:
  input_datasets: collection
steps:
  multi_data_optional:
    tool_id: multi_data_optional
    in:
      input1: input_datasets
"""
        )
        with self.dataset_populator.test_history() as history_id:
            hdca_id = self.dataset_collection_populator.create_list_of_list_in_history(history_id).json()
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            inputs = {
                "0": self._ds_entry(hdca_id),
            }
            invocation_id = self.__invoke_workflow(workflow_id, inputs=inputs, history_id=history_id)
            self.workflow_populator.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)
            output_collection = self.dataset_populator.get_history_collection_details(history_id, hid=6)
            assert output_collection["collection_type"] == "list"
            assert output_collection["job_source_type"] == "ImplicitCollectionJobs"

    @skip_without_tool("cat_list")
    @skip_without_tool("collection_creates_pair")
    def test_workflow_run_output_collection_mapping(self):
        workflow_id = self._upload_yaml_workflow(WORKFLOW_WITH_OUTPUT_COLLECTION_MAPPING)
        with self.dataset_populator.test_history() as history_id:
            fetch_response = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["a\nb\nc\nd\n", "e\nf\ng\nh\n"]
            ).json()
            hdca1 = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            inputs = {
                "0": self._ds_entry(hdca1),
            }
            invocation_id = self.__invoke_workflow(workflow_id, inputs=inputs, history_id=history_id)
            self.workflow_populator.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)
            assert "a\nc\nb\nd\ne\ng\nf\nh\n" == self.dataset_populator.get_history_dataset_content(history_id, hid=0)

    @skip_without_tool("cat_list")
    @skip_without_tool("collection_split_on_column")
    def test_workflow_run_dynamic_output_collections(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(WORKFLOW_WITH_DYNAMIC_OUTPUT_COLLECTION, history_id=history_id, assert_ok=True, wait=True)
            details = self.dataset_populator.get_history_dataset_details(history_id, hid=0)
            last_item_hid = details["hid"]
            assert last_item_hid == 7, f"Expected 7 history items, got {last_item_hid}"
            content = self.dataset_populator.get_history_dataset_content(history_id, hid=0)
            assert "10.0\n30.0\n20.0\n40.0\n" == content

    @skip_without_tool("collection_split_on_column")
    @skip_without_tool("min_repeat")
    def test_workflow_run_dynamic_output_collections_2(self):
        # A more advanced output collection workflow, testing regression of
        # https://github.com/galaxyproject/galaxy/issues/776
        with self.dataset_populator.test_history() as history_id:
            workflow_id = self._upload_yaml_workflow(
                """
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
"""
            )
            hda1 = self.dataset_populator.new_dataset(history_id, content="samp1\t10.0\nsamp2\t20.0\n")
            hda2 = self.dataset_populator.new_dataset(history_id, content="samp1\t20.0\nsamp2\t40.0\n")
            hda3 = self.dataset_populator.new_dataset(history_id, content="samp1\t30.0\nsamp2\t60.0\n")
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            inputs = {
                "0": self._ds_entry(hda1),
                "1": self._ds_entry(hda2),
                "2": self._ds_entry(hda3),
            }
            invocation_id = self.__invoke_workflow(workflow_id, inputs=inputs, history_id=history_id)
            self.workflow_populator.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)
            collection_details = self.dataset_populator.get_history_collection_details(history_id, hid=7)
            assert collection_details["populated_state"] == "ok"
            content = self.dataset_populator.get_history_dataset_content(history_id, hid=11)
            assert content.strip() == "samp1\t10.0\nsamp2\t20.0"

    @skip_without_tool("cat")
    @skip_without_tool("collection_split_on_column")
    def test_workflow_run_dynamic_output_collections_3(self):
        # Test a workflow that create a list:list:list followed by a mapping step.
        with self.dataset_populator.test_history() as history_id:
            workflow_id = self._upload_yaml_workflow(
                """
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
"""
            )
            hda1 = self.dataset_populator.new_dataset(history_id, content="samp1\t10.0\nsamp2\t20.0\n")
            hda2 = self.dataset_populator.new_dataset(history_id, content="samp1\t30.0\nsamp2\t40.0\n")
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            inputs = {
                "0": self._ds_entry(hda1),
                "1": self._ds_entry(hda2),
            }
            invocation_id = self.__invoke_workflow(workflow_id, inputs=inputs, history_id=history_id)
            self.workflow_populator.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)

    @skip_without_tool("cat1")
    @skip_without_tool("__FLATTEN__")
    def test_workflow_input_tags(self):
        workflow = self.workflow_populator.load_workflow_from_resource(name="test_workflow_with_input_tags")
        workflow_id = self.workflow_populator.create_workflow(workflow)
        downloaded_workflow = self._download_workflow(workflow_id)
        count = 0
        tag_test = ["tag1", "tag2"]
        for step in downloaded_workflow["steps"]:
            current = json.loads(downloaded_workflow["steps"][step]["tool_state"])
            assert current["tag"] == tag_test[count]
            count += 1

    @skip_without_tool("column_param")
    def test_empty_file_data_column_specified(self):
        # Regression test for https://github.com/galaxyproject/galaxy/pull/10981
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """class: GalaxyWorkflow
steps:
  empty_output:
    tool_id: empty_output
    outputs:
      out_file1:
        change_datatype: tabular
  column_param:
    tool_id: column_param
    in:
      input1: empty_output/out_file1
    state:
      col: 2
      col_names: 'B'
""",
                history_id=history_id,
            )

    @skip_without_tool("column_param_list")
    def test_comma_separated_columns(self):
        # Regression test for https://github.com/galaxyproject/galaxy/pull/10981
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """class: GalaxyWorkflow
steps:
  empty_output:
    tool_id: empty_output
    outputs:
      out_file1:
        change_datatype: tabular
  column_param_list:
    tool_id: column_param_list
    in:
      input1: empty_output/out_file1
    state:
      col: '2,3'
      col_names: 'B'
""",
                history_id=history_id,
            )

    @skip_without_tool("column_param_list")
    def test_comma_separated_columns_with_trailing_newline(self):
        # Tests that workflows with weird tool state continue to run.
        # In this case the newline may have been added by the workflow editor
        # text field that is used for data_column parameters
        with self.dataset_populator.test_history() as history_id:
            job_summary = self._run_workflow(
                """class: GalaxyWorkflow
steps:
  empty_output:
    tool_id: empty_output
    outputs:
      out_file1:
        change_datatype: tabular
  column_param_list:
    tool_id: column_param_list
    in:
      input1: empty_output/out_file1
    state:
      col: '2,3\n'
      col_names: 'B\n'
""",
                history_id=history_id,
            )
            job = self.dataset_populator.get_job_details(job_summary.jobs[0]["id"], full=True).json()
            assert "col 2,3" in job["command_line"]
            assert 'echo "col_names B" >>' in job["command_line"]

    @skip_without_tool("column_param")
    def test_runtime_data_column_parameter(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_workflow_with_runtime_data_column_parameter(history_id)

    @skip_without_tool("mapper")
    @skip_without_tool("pileup")
    def test_workflow_metadata_validation_0(self):
        # Testing regression of
        # https://github.com/galaxyproject/galaxy/issues/1514
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
    collection_type: list
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
""",
                history_id=history_id,
            )

    def test_run_workflow_pick_value_bam_pja(self):
        # Makes sure that setting metadata on expression tool data outputs
        # doesn't break result evaluation.
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """class: GalaxyWorkflow
inputs:
  some_file:
    type: data
steps:
  pick_value:
    tool_id: pick_value
    in:
      style_cond|type_cond|pick_from_0|value:
        source: some_file
    out:
      data_param:
        change_datatype: bam
    tool_state:
      style_cond:
        pick_style: first_or_error
        type_cond:
          param_type: data
          pick_from:
          - value:
            __class__: RuntimeValue
  consume_index:
    tool_id: metadata_bam
    in:
      input_bam: pick_value/data_param
    tool_state:
      ref_names:
        - chr10_random
        - chr11
        - chrM
        - chrX
        - chr16
outputs:
  pick_out:
    outputSource: pick_value/data_param
""",
                test_data="""
some_file:
  value: 3.bam
  file_type: unsorted.bam
  type: File
""",
                history_id=history_id,
            )
        invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
        # Make sure metadata is actually available
        pick_value_hda = invocation_details["outputs"]["pick_out"]
        dataset_details = self.dataset_populator.get_history_dataset_details(
            history_id=history_id, content_id=pick_value_hda["id"]
        )
        assert dataset_details["metadata_reference_names"]
        assert dataset_details["metadata_bam_index"]
        assert dataset_details["file_ext"] == "bam"

    def test_run_workflow_simple_conditional_step(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """class: GalaxyWorkflow
inputs:
  should_run:
    type: boolean
  some_file:
    type: data
steps:
  cat1:
    tool_id: cat1
    in:
      input1: some_file
      should_run: should_run
    when: $(inputs.should_run)
""",
                test_data="""
some_file:
  value: 1.bed
  type: File
should_run:
  value: false
  type: raw
""",
                history_id=history_id,
            )
            invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            for step in invocation_details["steps"]:
                if step["workflow_step_label"] == "cat1":
                    assert sum(1 for j in step["jobs"] if j["state"] == "skipped") == 1

    def test_run_workflow_simple_conditional_step_with_nested_tool_state(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """class: GalaxyWorkflow
inputs:
  should_run:
    type: boolean
  some_file:
    type: data
steps:
  nested_tool_state:
    tool_id: identifier_multiple_in_conditional
    state:
      outer_cond:
        cond_param_outer: true
        inner_cond:
          cond_param_inner: true
          input1:
            $link: some_file
    in:
      should_run: should_run
    when: $(inputs.should_run)
""",
                test_data="""
some_file:
  value: 1.bed
  type: File
should_run:
  value: false
  type: raw
""",
                history_id=history_id,
            )
            invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            for step in invocation_details["steps"]:
                if step["workflow_step_label"] == "identifier_multiple_in_conditional":
                    assert sum(1 for j in step["jobs"] if j["state"] == "skipped") == 1

    def test_run_workflow_invalid_when_expression(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """class: GalaxyWorkflow
inputs:
  should_run:
    type: boolean
  some_file:
    type: data
steps:
  cat1:
    tool_id: cat1
    in:
      input1: some_file
      should_run: should_run
    when: $(:syntaxError:)
""",
                test_data="""
some_file:
  value: 1.bed
  type: File
should_run:
  value: false
  type: raw
""",
                history_id=history_id,
                wait=True,
                assert_ok=False,
            )
            invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            assert invocation_details["state"] == "failed"
            assert len(invocation_details["messages"]) == 1
            message = invocation_details["messages"][0]
            assert message["reason"] == "expression_evaluation_failed"

    def test_run_workflow_fails_when_expression_not_boolean(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """class: GalaxyWorkflow
inputs:
  should_run:
    type: boolean
  some_file:
    type: data
steps:
  cat1:
    tool_id: cat1
    in:
      input1: some_file
      should_run: should_run
    when: $("false")
""",
                test_data="""
some_file:
  value: 1.bed
  type: File
should_run:
  value: false
  type: raw
""",
                history_id=history_id,
                wait=True,
                assert_ok=False,
            )
            invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            assert invocation_details["state"] == "failed"
            assert len(invocation_details["messages"]) == 1
            message = invocation_details["messages"][0]
            assert message["reason"] == "when_not_boolean"
            assert message["details"] == "Type is: str"
            assert message["workflow_step_id"] == 2

    def test_run_workflow_subworkflow_conditional_with_simple_mapping_step(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """class: GalaxyWorkflow
inputs:
  should_run:
    type: boolean
  some_collection:
    type: data_collection
steps:
  subworkflow:
    run:
      class: GalaxyWorkflow
      inputs:
        some_collection:
          type: data_collection
        should_run:
          type: boolean
      steps:
        a_tool_step:
          tool_id: cat1
          in:
            input1: some_collection
    in:
      some_collection: some_collection
      should_run: should_run
    outputs:
      inner_out: a_tool_step/out_file1
    when: $(inputs.should_run)
outputs:
  outer_output:
    outputSource: subworkflow/inner_out
""",
                test_data="""
some_collection:
  collection_type: list
  elements:
    - identifier: true
      content: A
    - identifier: false
      content: B
  type: File
should_run:
  value: false
  type: raw
""",
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )
            invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            subworkflow_invocation_id = invocation_details["steps"][-1]["subworkflow_invocation_id"]
            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id=history_id, workflow_id="whatever", invocation_id=subworkflow_invocation_id
            )
            invocation_details = self.workflow_populator.get_invocation(subworkflow_invocation_id, step_details=True)
            for step in invocation_details["steps"]:
                if step["workflow_step_label"] == "a_tool_step":
                    assert sum(1 for j in step["jobs"] if j["state"] == "skipped") == 2

    def test_run_workflow_subworkflow_conditional_step(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """class: GalaxyWorkflow
inputs:
  should_run:
    type: boolean
  some_file:
    type: data
steps:
  subworkflow:
    run:
      class: GalaxyWorkflow
      inputs:
        some_file:
          type: data
        should_run:
          type: boolean
      steps:
        a_tool_step:
          tool_id: cat1
          in:
            input1: some_file
    in:
      some_file: some_file
      should_run: should_run
    outputs:
      inner_out: a_tool_step/out_file1
    when: $(inputs.should_run)
outputs:
  outer_output:
    outputSource: subworkflow/inner_out
""",
                test_data="""
some_file:
  value: 1.bed
  type: File
should_run:
  value: false
  type: raw
""",
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )
            invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            subworkflow_invocation_id = invocation_details["steps"][-1]["subworkflow_invocation_id"]
            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id=history_id, workflow_id="whatever", invocation_id=subworkflow_invocation_id
            )
            invocation_details = self.workflow_populator.get_invocation(subworkflow_invocation_id, step_details=True)
            for step in invocation_details["steps"]:
                if step["workflow_step_label"] == "a_tool_step":
                    assert sum(1 for j in step["jobs"] if j["state"] == "skipped") == 1

    def test_run_nested_conditional_workflow_steps(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  dataset:
    type: data
  when:
    type: boolean
outputs:
  output:
    outputSource: outer_subworkflow/output
steps:
- label: outer_subworkflow
  when: $(inputs.when)
  in:
    dataset:
      source: dataset
    when:
      source: when
  run:
    class: GalaxyWorkflow
    label: subworkflow cat1
    inputs:
      dataset:
        type: data
    outputs:
      output:
        outputSource: cat1_workflow/output
    steps:
    - label: cat1_workflow
      in:
        dataset:
          source: dataset
      run:
        class: GalaxyWorkflow
        label: cat1
        inputs:
          dataset:
            type: data
        outputs:
          output:
            outputSource: cat1/out_file1
        steps:
        - tool_id: cat1
          label: cat1
          in:
            input1:
              source: dataset
""",
                test_data="""
dataset:
  value: 1.bed
  type: File
when:
  value: false
  type: raw
""",
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )
            invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            subworkflow_invocation_id = invocation_details["steps"][-1]["subworkflow_invocation_id"]
            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id=history_id, workflow_id="whatever", invocation_id=subworkflow_invocation_id
            )
            invocation_details = self.workflow_populator.get_invocation(subworkflow_invocation_id, step_details=True)
            subworkflow_invocation_id = invocation_details["steps"][-1]["subworkflow_invocation_id"]
            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id=history_id, workflow_id="whatever", invocation_id=subworkflow_invocation_id
            )
            invocation_details = self.workflow_populator.get_invocation(subworkflow_invocation_id, step_details=True)
            for step in invocation_details["steps"]:
                if step["workflow_step_label"] == "cat1":
                    assert sum(1 for j in step["jobs"] if j["state"] == "skipped") == 1

    def test_run_workflow_conditional_subworkflow_step_with_hdca_creation(self):
        # Regression test, ensures scheduling proceeds even if a skipped step creates a collection
        with self.dataset_populator.test_history() as history_id:
            self._run_workflow(
                """
class: GalaxyWorkflow
inputs: []
steps:
  conditional_subworkflow_step:
    when: $(false)
    run:
      class: GalaxyWorkflow
      inputs: []
      steps:
        create_collection:
          tool_id: create_input_collection
        flatten_collection:
          tool_id: cat_list
          in:
            input1: create_collection/output
                           """,
                history_id=history_id,
            )

    def test_run_workflow_conditional_step_map_over_expression_tool(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  boolean_input_files: collection
steps:
- label: param_out
  tool_id: param_value_from_file
  in:
     input1: boolean_input_files
  state:
    param_type: boolean
- label: consume_expression_parameter
  tool_id: cat1
  in:
    input1: boolean_input_files
    should_run: param_out/boolean_param
  out:
    out_file1:
      change_datatype: txt
  when: $(inputs.should_run)
test_data:
  boolean_input_files:
    collection_type: list
    elements:
      - identifier: true
        content: true
      - identifier: false
        content: false
""",
                history_id=history_id,
            )
            invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            for step in invocation_details["steps"]:
                if step["workflow_step_label"] == "consume_expression_parameter":
                    skipped_jobs = [j for j in step["jobs"] if j["state"] == "skipped"]
                    assert len(skipped_jobs) == 1
                    # also assert that change_datatype was ignored for null output
                    job_details = self.dataset_populator.get_job_details(skipped_jobs[0]["id"], full=True).json()
                    skipped_hda_id = job_details["outputs"]["out_file1"]["id"]
                    dataset_details = self.dataset_populator.get_history_dataset_details(
                        history_id=history_id, content_id=skipped_hda_id
                    )
                    assert dataset_details["file_ext"] == "expression.json", dataset_details

    def test_run_workflow_conditional_subworkflow_step_map_over_expression_tool(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  boolean_input_files: collection
steps:
  create_list_of_boolean:
    tool_id: param_value_from_file
    in:
       input1: boolean_input_files
    state:
      param_type: boolean
  subworkflow:
    run:
      class: GalaxyWorkflow
      inputs:
        boolean_input_file: data
        should_run: boolean
      steps:
        consume_expression_parameter:
          tool_id: cat1
          in:
            input1: boolean_input_file
          out:
            out_file1:
              change_datatype: txt
      outputs:
        inner_output:
          outputSource: consume_expression_parameter/out_file1
    in:
      boolean_input_file: boolean_input_files
      should_run: create_list_of_boolean/boolean_param
    when: $(inputs.should_run)
outputs:
  outer_output:
    outputSource: subworkflow/inner_output
test_data:
  boolean_input_files:
    collection_type: list
    elements:
      - identifier: true
        content: true
      - identifier: false
        content: false
""",
                history_id=history_id,
            )
            invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            assert "outer_output" in invocation_details["output_collections"]
            outer_output = invocation_details["output_collections"]["outer_output"]
            outer_hdca = self.dataset_populator.get_history_collection_details(
                history_id, content_id=outer_output["id"]
            )
            assert outer_hdca["job_state_summary"]["all_jobs"] == 2
            assert outer_hdca["job_state_summary"]["ok"] == 1
            assert outer_hdca["job_state_summary"]["skipped"] == 1

    def test_run_workflow_conditional_subworkflow_step_map_over_expression_tool_with_extra_nesting(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                NESTED_WORKFLOW_WITH_CONDITIONAL_SUBWORKFLOW_AND_DISCONNECTED_MAP_OVER_SOURCE,
                test_data="""boolean_input_files:
  collection_type: list
  elements:
    - identifier: true
      content: true
    - identifier: false
      content: false
""",
                history_id=history_id,
            )
            invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            outer_create_nested_id = invocation_details["output_collections"]["outer_create_nested"]["id"]
            outer_create_nested = self.dataset_populator.get_history_collection_details(
                history_id, content_id=outer_create_nested_id
            )
            assert outer_create_nested["job_state_summary"]["all_jobs"] == 2
            assert outer_create_nested["job_state_summary"]["ok"] == 1
            assert outer_create_nested["job_state_summary"]["skipped"] == 1

            for cat1_output in ["outer_output_1", "outer_output_2"]:
                outer_output = invocation_details["output_collections"][cat1_output]
                outer_hdca = self.dataset_populator.get_history_collection_details(
                    history_id, content_id=outer_output["id"]
                )
                # You might expect 12 total jobs, 6 ok and 6 skipped,
                # but because we're not actually running one branch of collection_creates_dynamic_nested
                # there's no input to consume_expression_parameter.
                # It's unclear if that's a problem or not ... probably not a major one,
                # since we keep producing "empty" outer collections, which seems somewhat correct.
                assert outer_hdca["job_state_summary"]["all_jobs"] == 6
                assert outer_hdca["job_state_summary"]["ok"] == 6
                assert outer_hdca["collection_type"] == "list:list:list"
                elements = outer_hdca["elements"]
                assert elements[0]["element_identifier"] == "True"
                assert elements[0]["object"]["element_count"] == 3
                assert elements[1]["element_identifier"] == "False"
                assert elements[1]["object"]["element_count"] == 0

    def test_run_workflow_conditional_subworkflow_step_map_over_expression_tool_with_extra_nesting_skip_all(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                NESTED_WORKFLOW_WITH_CONDITIONAL_SUBWORKFLOW_AND_DISCONNECTED_MAP_OVER_SOURCE,
                test_data="""boolean_input_files:
  collection_type: list
  elements:
    - identifier: false
      content: false
    - identifier: also_false
      content: false
""",
                history_id=history_id,
            )
            invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            outer_create_nested_id = invocation_details["output_collections"]["outer_create_nested"]["id"]
            outer_create_nested = self.dataset_populator.get_history_collection_details(
                history_id, content_id=outer_create_nested_id
            )
            assert outer_create_nested["job_state_summary"]["all_jobs"] == 2
            assert outer_create_nested["job_state_summary"]["skipped"] == 2

            for cat1_output in ["outer_output_1", "outer_output_2"]:
                outer_output = invocation_details["output_collections"][cat1_output]
                outer_hdca = self.dataset_populator.get_history_collection_details(
                    history_id, content_id=outer_output["id"]
                )
                assert outer_hdca["job_state_summary"]["all_jobs"] == 0
                assert outer_hdca["collection_type"] == "list:list:list"

    def test_run_workflow_conditional_step_map_over_expression_tool_pick_value(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  boolean_input_files_1: collection
  boolean_input_files_2: collection
outputs:
  my_output:
    outputSource: pick_value/data_param
steps:
- label: param_out_1
  tool_id: param_value_from_file
  in:
     input1: boolean_input_files_1
  state:
    param_type: boolean
- label: param_out_2
  tool_id: param_value_from_file
  in:
     input1: boolean_input_files_2
  state:
    param_type: boolean
- label: consume_expression_parameter_1
  tool_id: cat1
  in:
    input1: boolean_input_files_1
    should_run: param_out_1/boolean_param
  when: $(inputs.should_run)
- label: consume_expression_parameter_2
  tool_id: cat1
  in:
    input1: boolean_input_files_2
    should_run: param_out_2/boolean_param
  when: $(inputs.should_run)
- label: pick_value
  tool_id: pick_value
  tool_state:
    style_cond:
      __current_case__: 2
      pick_style: first_or_error
      type_cond:
        __current_case__: 4
        param_type: data
        pick_from:
        - __index__: 0
          value:
            __class__: RuntimeValue
        - __index__: 1
          value:
            __class__: RuntimeValue
  in:
    style_cond|type_cond|pick_from_0|value:
      source: consume_expression_parameter_1/out_file1
    style_cond|type_cond|pick_from_1|value:
      source: consume_expression_parameter_2/out_file1
test_data:
  boolean_input_files_1:
    collection_type: list
    elements:
      - identifier: true
        content: true
      - identifier: false
        content: false
  boolean_input_files_2:
    collection_type: list
    elements:
      - identifier: false
        content: false
      - identifier: true
        content: true
""",
                history_id=history_id,
            )
            invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            output_collection_id = invocation_details["output_collections"]["my_output"]["id"]
            hdca_details = self.dataset_populator.get_history_collection_details(
                history_id=history_id, content_id=output_collection_id
            )
            elements = hdca_details["elements"]
            assert len(elements) == 2
            for element in elements:
                content = self.dataset_populator.get_history_dataset_content(
                    history_id, content_id=element["object"]["id"]
                )
                assert content == "True"
            for step in invocation_details["steps"]:
                if step["workflow_step_label"].startswith("consume_expression_parameter_"):
                    assert sum(1 for j in step["jobs"] if j["state"] == "skipped") == 1

    def test_run_subworkflow_simple(self) -> None:
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                WORKFLOW_NESTED_SIMPLE,
                test_data="""
outer_input:
  value: 1.bed
  type: File
""",
                history_id=history_id,
            )
            invocation_id = summary.invocation_id

            content = self.dataset_populator.get_history_dataset_content(history_id)
            assert (
                content
                == "chrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\nchrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\n"
            )
            steps = self.workflow_populator.get_invocation(invocation_id)["steps"]
            assert sum(1 for step in steps if step["subworkflow_invocation_id"] is None) == 3
            subworkflow_invocation_id = [
                step["subworkflow_invocation_id"] for step in steps if step["subworkflow_invocation_id"]
            ][0]
            subworkflow_invocation = self.workflow_populator.get_invocation(subworkflow_invocation_id)
            assert subworkflow_invocation["steps"][0]["workflow_step_label"] == "inner_input"
            assert subworkflow_invocation["steps"][1]["workflow_step_label"] == "random_lines"

    @skip_without_tool("random_lines1")
    def test_run_subworkflow_runtime_parameters(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                WORKFLOW_NESTED_RUNTIME_PARAMETER,
                test_data="""
step_parameters:
  '1':
    '1|num_lines': 2
outer_input:
  value: 1.bed
  type: File
""",
                history_id=history_id,
            )

            content = self.dataset_populator.get_history_dataset_content(history_id)
            assert len([x for x in content.split("\n") if x]) == 2

    @skip_without_tool("cat")
    def test_run_subworkflow_replacement_parameters(self):
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
            workflow_run_description = f"""{WORKFLOW_RUNTIME_PARAMETER_AFTER_PAUSE}

test_data:
  step_parameters:
    '2':
      'num_lines': 2
  input1:
    value: 1.bed
    type: File
"""
            job_summary = self._run_workflow(workflow_run_description, history_id=history_id, wait=False)
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
            invocation_scheduled = self._wait_for_invocation_state(uploaded_workflow_id, invocation_id, "scheduled")
            assert invocation_scheduled, "Workflow state is not scheduled..."
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            content = self.dataset_populator.get_history_dataset_content(history_id)
            assert len([x for x in content.split("\n") if x]) == 2

    def test_run_subworkflow_auto_labels(self):
        def run_test(workflow_text):
            with self.dataset_populator.test_history() as history_id:
                test_data = """
        outer_input:
          value: 1.bed
          type: File
        """
                summary = self._run_workflow(workflow_text, test_data=test_data, history_id=history_id)
                jobs = summary.jobs
                num_jobs = len(jobs)
                assert num_jobs == 2, f"2 jobs expected, got {num_jobs} jobs"

                content = self.dataset_populator.get_history_dataset_content(history_id)
                assert (
                    content
                    == "chrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\nchrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\n"
                )

        run_test(NESTED_WORKFLOW_AUTO_LABELS_MODERN_SYNTAX)

    @skip_without_tool("cat")
    def test_workflow_invocation_report_1(self):
        test_data = """
input_1:
  value: 1.bed
  type: File
"""
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input_1: data
outputs:
  output_1:
    outputSource: first_cat/out_file1
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input_1
""",
                test_data=test_data,
                history_id=history_id,
            )
            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            report_json = self.workflow_populator.workflow_report_json(workflow_id, invocation_id)
            assert "markdown" in report_json
            self._assert_has_keys(report_json, "markdown", "render_format")
            assert report_json["render_format"] == "markdown"
            markdown_content = report_json["markdown"]
            assert "## Workflow Outputs" in markdown_content
            assert "## Workflow Inputs" in markdown_content
            assert "## About This Report" not in markdown_content
            with self._different_user():
                exception_raised = False
                try:
                    self.workflow_populator.workflow_report_json(workflow_id, invocation_id)
                except AssertionError as e:
                    if "Request status code (403)" in str(e):
                        exception_raised = True
            assert exception_raised, "Expected workflow report request to fail, but it didn't"
            self.dataset_populator.make_public(history_id)
            self.workflow_populator.make_public(workflow_id)
            with self._different_user():
                self.workflow_populator.workflow_report_json(workflow_id, invocation_id)

    @skip_without_tool("cat")
    def test_workflow_invocation_report_custom(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                WORKFLOW_WITH_CUSTOM_REPORT_1, test_data=WORKFLOW_WITH_CUSTOM_REPORT_1_TEST_DATA, history_id=history_id
            )
            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            downloaded_workflow = self._download_workflow(workflow_id)
            assert "report" in downloaded_workflow
            report_config = downloaded_workflow["report"]
            assert "markdown" in report_config
            report_json = self.workflow_populator.workflow_report_json(workflow_id, invocation_id)
            assert "markdown" in report_json, f"markdown not in report json {report_json}"
            self._assert_has_keys(report_json, "markdown", "render_format")
            assert report_json["render_format"] == "markdown"
            markdown_content = report_json["markdown"]
            assert "## Workflow Outputs" in markdown_content
            assert "\n```galaxy\nhistory_dataset_display(history_dataset_id=" in markdown_content
            assert "## Workflow Inputs" in markdown_content
            assert "## About This Report" in markdown_content

    @skip_without_tool("cat1")
    def test_export_invocation_bco(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(WORKFLOW_SIMPLE, test_data={"input1": "hello world"}, history_id=history_id)
            invocation_id = summary.invocation_id
            bco_path = self.workflow_populator.download_invocation_to_store(invocation_id, extension="bco.json")
            with open(bco_path) as f:
                bco = json.load(f)
            self.workflow_populator.validate_biocompute_object(bco)
            assert bco["provenance_domain"]["name"] == "Simple Workflow"

    @skip_without_tool("cat1")
    def test_export_invocation_ro_crate(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(WORKFLOW_SIMPLE, test_data={"input1": "hello world"}, history_id=history_id)
            invocation_id = summary.invocation_id
            crate = self.workflow_populator.get_ro_crate(invocation_id, include_files=True)
            workflow = crate.mainEntity
            assert workflow

    @skip_without_tool("__MERGE_COLLECTION__")
    def test_merge_collection_scheduling(self, history_id):
        summary = self._run_workflow(
            """
class: GalaxyWorkflow
inputs:
  collection:
    type: collection
    collection_type: list
outputs:
  merge_out:
    outputSource: merge/output
steps:
  sleep:
    tool_id: cat_data_and_sleep
    in:
      input1: collection
    state:
      sleep_time: 5
  merge:
    tool_id: __MERGE_COLLECTION__
    in:
      inputs_1|input: sleep/out_file1
      inputs_0|input: sleep/out_file1
test_data:
  collection:
    collection_type: list
    elements:
      - identifier: 1
        content: A
""",
            history_id=history_id,
            wait=True,
            assert_ok=True,
        )
        invocation = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
        merge_out_id = invocation["output_collections"]["merge_out"]["id"]
        merge_out = self.dataset_populator.get_history_collection_details(history_id, content_id=merge_out_id)
        assert merge_out["element_count"] == 1
        assert merge_out["elements"][0]["object"]["state"] == "ok"

    @skip_without_tool("__MERGE_COLLECTION__")
    @skip_without_tool("cat_collection")
    @skip_without_tool("head")
    def test_export_invocation_ro_crate_adv(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input collection 1:
    type: collection
    collection_type: list
    optional: false
  input collection 2:
    type: collection
    collection_type: list
    optional: false
  num_lines_param:
    type: int
    optional: false
    default: 2
outputs:
  _anonymous_output_1:
    outputSource: num_lines_param
  output_collection:
    outputSource: merge collections tool
  concatenated_collection:
    outputSource: concat collection/out_file1
  output:
    outputSource: select lines/out_file1
steps:
  merge collections tool:
    tool_id: __MERGE_COLLECTION__
    tool_version: 1.0.0
    tool_state:
      advanced:
        conflict:
          __current_case__: 0
          duplicate_options: keep_first
      inputs:
      - __index__: 0
        input:
          __class__: ConnectedValue
      - __index__: 1
        input:
          __class__: ConnectedValue
    in:
      inputs_1|input:
        source: input collection 2
      inputs_0|input:
        source: input collection 1
  concat collection:
    tool_id: cat_collection
    tool_state:
      input1:
        __class__: RuntimeValue
    in:
      input1:
        source: merge collections tool
  select lines:
    tool_id: head
    tool_state:
      input:
        __class__: RuntimeValue
      lineNum:
        __class__: ConnectedValue
    in:
      lineNum:
        source: num_lines_param
      input:
        source: concat collection/out_file1
""",
                test_data="""
num_lines_param:
  type: int
  value: 2
input collection 1:
  collection_type: list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
    - identifier: el2
      value: 1.fastq
      type: File
input collection 2:
  collection_type: list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
    - identifier: el2
      value: 1.fastq
      type: File
""",
                history_id=history_id,
                wait=True,
            )
            invocation_id = summary.invocation_id
            crate = self.workflow_populator.get_ro_crate(invocation_id, include_files=True)
            workflow = crate.mainEntity
            root = crate.root_dataset
            assert len(root["mentions"]) == 4
            actions = [_ for _ in crate.contextual_entities if "CreateAction" in _.type]
            assert len(actions) == 1
            wf_action = actions[0]
            wf_objects = wf_action["object"]
            assert len(workflow["input"]) == 3
            assert len(workflow["output"]) == 3
            collections = [_ for _ in crate.contextual_entities if "Collection" in _.type]
            assert len(collections) == 3
            collection = collections[0]
            assert (
                collection["additionalType"]
                == "https://training.galaxyproject.org/training-material/faqs/galaxy/collections_build_list.html"
            )
            assert collection.type == "Collection"
            assert len(collection["hasPart"]) == 2
            assert collection in wf_objects

            coll_dataset = collection["hasPart"][0].id
            assert coll_dataset in [_.id for _ in collections[2]["hasPart"]]
            property_values = [_ for _ in crate.contextual_entities if "PropertyValue" in _.type]
            assert len(property_values) == 1
            for pv in property_values:
                assert pv in wf_objects
                assert pv["exampleOfWork"] in workflow["input"]

    @skip_without_tool("__APPLY_RULES__")
    def test_workflow_run_apply_rules(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_workflow(
                WORKFLOW_WITH_RULES_1,
                history_id=history_id,
                wait=True,
                assert_ok=True,
                round_trip_format_conversion=True,
            )
            output_content = self.dataset_populator.get_history_collection_details(history_id, hid=6)
            rules_test_data.check_example_2(output_content, self.dataset_populator)

    def test_filter_failed_mapping(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """
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
        $link: mixed_collection/out_file1

  cat:
    tool_id: cat1
    state:
      input1:
        $link: filtered_collection
""",
                test_data="""
input_c:
  collection_type: list
  elements:
    - identifier: i1
      content: "0"
    - identifier: i2
      content: "1"
""",
                history_id=history_id,
                wait=True,
                assert_ok=False,
            )
            jobs = summary.jobs

            def filter_jobs_by_tool(tool_id):
                return [j for j in summary.jobs if j["tool_id"] == tool_id]

            assert len(filter_jobs_by_tool("exit_code_from_file")) == 2, jobs
            assert len(filter_jobs_by_tool("__FILTER_FAILED_DATASETS__")) == 1, jobs
            # Follow proves one job was filtered out of the result of cat1
            assert len(filter_jobs_by_tool("cat1")) == 1, jobs

    def test_keep_success_mapping_error(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input_c: collection

steps:
  mixed_collection:
    tool_id: exit_code_from_file
    in:
       input: input_c

  filtered_collection:
    tool_id: "__KEEP_SUCCESS_DATASETS__"
    in:
      input: mixed_collection/out_file1

  cat:
    tool_id: cat1
    in:
      input1: filtered_collection/output
""",
                test_data="""
input_c:
  collection_type: list
  elements:
    - identifier: i1
      content: "0"
    - identifier: i2
      content: "1"
""",
                history_id=history_id,
                wait=True,
                assert_ok=False,
            )
            jobs = summary.jobs

            def filter_jobs_by_tool(tool_id):
                return [j for j in summary.jobs if j["tool_id"] == tool_id]

            assert len(filter_jobs_by_tool("exit_code_from_file")) == 2, jobs
            assert len(filter_jobs_by_tool("__KEEP_SUCCESS_DATASETS__")) == 1, jobs
            # Follow proves one job was filtered out of the exit_code_from_file
            # And a single one has been sent to cat1
            assert len(filter_jobs_by_tool("cat1")) == 1, jobs

    def test_keep_success_mapping_paused(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input_c: collection

steps:
  mixed_collection:
    tool_id: exit_code_from_file
    in:
       input: input_c

  cat:
    tool_id: cat1
    in:
      input1: mixed_collection/out_file1

  filtered_collection:
    tool_id: "__KEEP_SUCCESS_DATASETS__"
    in:
      input: cat/out_file1
""",
                test_data="""
input_c:
  collection_type: list
  elements:
    - identifier: i1
      content: "0"
    - identifier: i2
      content: "1"
    - identifier: i3
      content: "0"
""",
                history_id=history_id,
                wait=True,
                assert_ok=False,
            )
            jobs = summary.jobs

            def filter_jobs_by_tool(tool_id):
                return [j for j in summary.jobs if j["tool_id"] == tool_id]

            # Get invocation to access output collections
            invocation = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            # Check there are 3 exit_code_from_file
            assert len(filter_jobs_by_tool("exit_code_from_file")) == 3, jobs
            # Check output collection has 3 elements
            output_mixed_collection_id = invocation["steps"][1]["output_collections"]["out_file1"]["id"]
            mixed_collection = self.dataset_populator.get_history_collection_details(
                history_id, content_id=output_mixed_collection_id, assert_ok=False
            )
            assert mixed_collection["element_count"] == 3, mixed_collection
            # Check 3 jobs cat1 has been "scheduled":
            assert len(filter_jobs_by_tool("cat1")) == 3, jobs
            # Check 2 are 'ok' the other is 'paused'
            output_cat_id = invocation["steps"][2]["output_collections"]["out_file1"]["id"]
            cat_collection = self.dataset_populator.get_history_collection_details(
                history_id, content_id=output_cat_id, assert_ok=False
            )
            assert cat_collection["element_count"] == 3, cat_collection
            cat1_states = [e["object"]["state"] for e in cat_collection["elements"]]
            assert "paused" in cat1_states, jobs
            assert len([s for s in cat1_states if s == "ok"]) == 2, cat_collection
            # Check the KEEP_SUCCESS_DATASETS have been run
            assert len(filter_jobs_by_tool("__KEEP_SUCCESS_DATASETS__")) == 1, jobs
            # Check the output has 2 elements
            output_filtered_id = invocation["steps"][3]["output_collections"]["output"]["id"]
            output_filtered = self.dataset_populator.get_history_collection_details(
                history_id, content_id=output_filtered_id, assert_ok=False
            )
            assert output_filtered["element_count"] == 2, output_filtered

    def test_workflow_request(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_queue")
        workflow_request, history_id, workflow_id = self._setup_workflow_run(workflow)
        run_workflow_response = self.workflow_populator.invoke_workflow_raw(
            workflow_id, workflow_request, assert_ok=True
        )
        invocation_id = run_workflow_response.json()["id"]
        self.workflow_populator.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)

    def test_workflow_request_recover(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_queue")
        workflow_request, history_id, workflow_id = self._setup_workflow_run(workflow)
        run_workflow_response = self.workflow_populator.invoke_workflow_raw(
            workflow_id, workflow_request, assert_ok=True
        )
        invocation_id = run_workflow_response.json()["id"]
        self.workflow_populator.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)
        request = self.workflow_populator.invocation_to_request(invocation_id)
        assert request["history_id"] == history_id
        assert request["replacement_params"] is None
        assert request["use_cached_job"] is False
        assert request["preferred_object_store_id"] is None
        assert request["preferred_intermediate_object_store_id"] is None
        assert request["preferred_outputs_object_store_id"] is None
        assert request["parameters_normalized"] is True
        assert request["parameters"] is None

        assert request["inputs"]["WorkflowInput1"]["src"] == "hda"
        encoded_id = request["inputs"]["WorkflowInput1"]["id"]
        assert self.dataset_populator.get_history_dataset_content(history_id, dataset_id=encoded_id).strip() == "1 2 3"
        assert request["inputs"]["WorkflowInput2"]["src"] == "hda"
        encoded_id = request["inputs"]["WorkflowInput2"]["id"]
        assert self.dataset_populator.get_history_dataset_content(history_id, dataset_id=encoded_id).strip() == "4 5 6"

    def test_workflow_new_autocreated_history(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_new_autocreated_history")
        workflow_request, history_id, workflow_id = self._setup_workflow_run(workflow)
        del workflow_request[
            "history"
        ]  # Not passing a history param means asking for a new history to be automatically created
        run_workflow_dict = self.workflow_populator.invoke_workflow_raw(
            workflow_id, workflow_request, assert_ok=True
        ).json()
        new_history_id = run_workflow_dict["history_id"]
        assert history_id != new_history_id
        invocation_id = run_workflow_dict["id"]
        self.workflow_populator.wait_for_invocation_and_jobs(new_history_id, workflow_id, invocation_id)

    def test_invocation_job_metrics_simple(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(WORKFLOW_SIMPLE, test_data={"input1": "hello world"}, history_id=history_id)
            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id=history_id, workflow_id=summary.workflow_id, invocation_id=summary.invocation_id
            )
            job_metrics = self._get(f"invocations/{summary.invocation_id}/metrics").json()
            galaxy_slots = [m for m in job_metrics if m["name"] == "galaxy_slots"]
            assert len(galaxy_slots) == 1

    def test_invocation_job_metrics_map_over(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                WORKFLOW_SIMPLE,
                test_data={
                    "input1": {
                        "collection_type": "list",
                        "name": "the_dataset_list",
                        "elements": [
                            {"identifier": "el1", "value": "1.fastq", "type": "File"},
                            {"identifier": "el2", "value": "1.fastq", "type": "File"},
                        ],
                    }
                },
                history_id=history_id,
            )
            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id=history_id, workflow_id=summary.workflow_id, invocation_id=summary.invocation_id
            )
            job_metrics = self._get(f"invocations/{summary.invocation_id}/metrics").json()
            galaxy_slots = [m for m in job_metrics if m["name"] == "galaxy_slots"]
            assert len(galaxy_slots) == 2

    def test_workflow_output_dataset(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(WORKFLOW_SIMPLE, test_data={"input1": "hello world"}, history_id=history_id)
            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            invocation_response = self._get(f"workflows/{workflow_id}/invocations/{invocation_id}")
            self._assert_status_code_is(invocation_response, 200)
            invocation = invocation_response.json()
            self._assert_has_keys(invocation, "id", "outputs", "output_collections")
            assert len(invocation["output_collections"]) == 0
            assert len(invocation["outputs"]) == 1
            output_content = self.dataset_populator.get_history_dataset_content(
                history_id, dataset_id=invocation["outputs"]["wf_output_1"]["id"]
            )
            assert "hello world" == output_content.strip()

    @skip_without_tool("cat")
    def test_workflow_output_dataset_collection(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow_with_output_collections(history_id)
            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            invocation_response = self._get(f"workflows/{workflow_id}/invocations/{invocation_id}")
            self._assert_status_code_is(invocation_response, 200)
            invocation = invocation_response.json()
            self._assert_has_keys(invocation, "id", "outputs", "output_collections")
            assert len(invocation["output_collections"]) == 1
            assert len(invocation["outputs"]) == 0
            output_content = self.dataset_populator.get_history_collection_details(
                history_id, content_id=invocation["output_collections"]["wf_output_1"]["id"]
            )
            self._assert_has_keys(output_content, "id", "elements")
            assert output_content["collection_type"] == "list"
            elements = output_content["elements"]
            assert len(elements) == 1
            elements0 = elements[0]
            assert elements0["element_identifier"] == "el1"

    def test_workflow_input_as_output(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow_with_inputs_as_outputs(history_id)
            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            invocation_response = self._get(f"workflows/{workflow_id}/invocations/{invocation_id}")
            self._assert_status_code_is(invocation_response, 200)
            invocation = invocation_response.json()
            self._assert_has_keys(invocation, "id", "outputs", "output_collections")
            assert len(invocation["output_collections"]) == 0
            assert len(invocation["outputs"]) == 1
            assert len(invocation["output_values"]) == 1
            assert "wf_output_param" in invocation["output_values"]
            assert invocation["output_values"]["wf_output_param"] == "A text variable", invocation["output_values"]
            output_content = self.dataset_populator.get_history_dataset_content(
                history_id, content_id=invocation["outputs"]["wf_output_1"]["id"]
            )
            assert output_content == "hello world\n"

    def test_subworkflow_output_as_output(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input1: data
outputs:
  wf_output_1:
    outputSource: nested_workflow/inner_output
steps:
  nested_workflow:
    run:
      class: GalaxyWorkflow
      inputs:
        inner_input: data
      outputs:
        inner_output:
          outputSource: inner_input
      steps: []
    in:
      inner_input: input1
""",
                test_data={"input1": "hello world"},
                history_id=history_id,
            )
            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            invocation_response = self._get(f"workflows/{workflow_id}/invocations/{invocation_id}")
            self._assert_status_code_is(invocation_response, 200)
            invocation = invocation_response.json()
            self._assert_has_keys(invocation, "id", "outputs", "output_collections")
            assert len(invocation["output_collections"]) == 0
            assert len(invocation["outputs"]) == 1
            output_content = self.dataset_populator.get_history_dataset_content(
                history_id, content_id=invocation["outputs"]["wf_output_1"]["id"]
            )
            assert output_content == "hello world\n"

    @skip_without_tool("cat")
    def test_workflow_input_mapping(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """
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
""",
                test_data="""
input1:
  collection_type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
    - identifier: el2
      value: 1.fastq
      type: File
""",
                history_id=history_id,
            )
            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            invocation_response = self._get(f"workflows/{workflow_id}/invocations/{invocation_id}")
            self._assert_status_code_is(invocation_response, 200)
            invocation = invocation_response.json()
            self._assert_has_keys(invocation, "id", "outputs", "output_collections")
            assert len(invocation["output_collections"]) == 1
            assert len(invocation["outputs"]) == 0
            output_content = self.dataset_populator.get_history_collection_details(
                history_id, content_id=invocation["output_collections"]["wf_output_1"]["id"]
            )
            self._assert_has_keys(output_content, "id", "elements")
            elements = output_content["elements"]
            assert len(elements) == 2
            elements0 = elements[0]
            assert elements0["element_identifier"] == "el1"

    @skip_without_tool("collection_creates_pair")
    def test_workflow_run_input_mapping_with_output_collections(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """
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
""",
                test_data="""
text_input:
  collection_type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
    - identifier: el2
      value: 1.fastq
      type: File
""",
                history_id=history_id,
            )
            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            invocation_response = self._get(f"workflows/{workflow_id}/invocations/{invocation_id}")
            self._assert_status_code_is(invocation_response, 200)
            invocation = invocation_response.json()
            self._assert_has_keys(invocation, "id", "outputs", "output_collections")
            assert len(invocation["output_collections"]) == 1
            assert len(invocation["outputs"]) == 0
            output_content = self.dataset_populator.get_history_collection_details(
                history_id, content_id=invocation["output_collections"]["wf_output_1"]["id"]
            )
            self._assert_has_keys(output_content, "id", "elements")
            assert output_content["collection_type"] == "list:paired", output_content
            elements = output_content["elements"]
            assert len(elements) == 2
            elements0 = elements[0]
            assert elements0["element_identifier"] == "el1"

            self.workflow_populator.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)

            jobs_summary_response = self._get(f"workflows/{workflow_id}/invocations/{invocation_id}/jobs_summary")
            self._assert_status_code_is(jobs_summary_response, 200)
            jobs_summary = jobs_summary_response.json()
            assert "states" in jobs_summary

            invocation_states = jobs_summary["states"]
            assert invocation_states and "ok" in invocation_states, jobs_summary
            assert invocation_states["ok"] == 2, jobs_summary
            assert jobs_summary["model"] == "WorkflowInvocation", jobs_summary

            jobs_summary_response = self._get(f"workflows/{workflow_id}/invocations/{invocation_id}/step_jobs_summary")
            self._assert_status_code_is(jobs_summary_response, 200)
            jobs_summary = jobs_summary_response.json()
            assert len(jobs_summary) == 1
            collection_summary = jobs_summary[0]
            assert "states" in collection_summary

            collection_states = collection_summary["states"]
            assert collection_states and "ok" in collection_states, collection_states
            assert collection_states["ok"] == 2, collection_summary
            assert collection_summary["model"] == "ImplicitCollectionJobs", collection_summary

    def test_workflow_run_input_mapping_with_subworkflows(self):
        with self.dataset_populator.test_history() as history_id:
            test_data = """
outer_input:
  collection_type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
    - identifier: el2
      value: 1.fastq
      type: File
"""
            summary = self._run_workflow(WORKFLOW_NESTED_SIMPLE, test_data=test_data, history_id=history_id)
            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            invocation_response = self._get(f"workflows/{workflow_id}/invocations/{invocation_id}")
            self._assert_status_code_is(invocation_response, 200)
            invocation_response = self._get(f"workflows/{workflow_id}/invocations/{invocation_id}")
            self._assert_status_code_is(invocation_response, 200)
            invocation = invocation_response.json()
            self._assert_has_keys(invocation, "id", "outputs", "output_collections")
            assert len(invocation["output_collections"]) == 1, invocation
            assert len(invocation["outputs"]) == 0
            output_content = self.dataset_populator.get_history_collection_details(
                history_id, content_id=invocation["output_collections"]["outer_output"]["id"]
            )
            self._assert_has_keys(output_content, "id", "elements")
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
            self._run_workflow(
                """
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
""",
                history_id=history_id,
                wait=True,
                round_trip_format_conversion=True,
            )
            assert (
                self.dataset_populator.get_history_dataset_content(history_id)
                == "chr6\t108722976\t108723115\tCCDS5067.1_cds_0_0_chr6_108722977_f\t0\t+\nchrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\n"
            )
            # assert self.dataset_populator.get_history_dataset_content(history_id) == "chr16\t142908\t143003\tCCDS10397.1_cds_0_0_chr16_142909_f\t0\t+\nchrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\n"

    @skip_without_tool("cat_list")
    @skip_without_tool("random_lines1")
    @skip_without_tool("split")
    def test_subworkflow_recover_mapping_2(self):
        # Like the above test case, this test case tests an outer workflow continues to
        # schedule and handle collection mapping properly after a subworkflow needs to be
        # delayed, but this also tests recovering and handling scheduling within the subworkflow
        # since the delayed step (split) isn't the last step of the subworkflow.
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
""",
                test_data="""
outer_input:
  value: 1.bed
  type: File
""",
                history_id=history_id,
                wait=True,
                round_trip_format_conversion=True,
            )
            assert (
                self.dataset_populator.get_history_dataset_content(history_id)
                == "chr6\t108722976\t108723115\tCCDS5067.1_cds_0_0_chr6_108722977_f\t0\t+\nchrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\n"
            )

    @skip_without_tool("cat_list")
    @skip_without_tool("random_lines1")
    @skip_without_tool("split")
    def test_recover_mapping_in_subworkflow(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
""",
                test_data="""
outer_input:
  value: 1.bed
  type: File
""",
                history_id=history_id,
                wait=True,
                round_trip_format_conversion=True,
            )
            assert (
                self.dataset_populator.get_history_dataset_content(history_id)
                == "chr6\t108722976\t108723115\tCCDS5067.1_cds_0_0_chr6_108722977_f\t0\t+\nchrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\n"
            )

    @skip_without_tool("empty_list")
    @skip_without_tool("count_list")
    @skip_without_tool("random_lines1")
    def test_empty_list_mapping(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
        $link: empty_list/output
      seed_source:
        seed_source_selector: set_seed
        seed: asdf
  count_list:
    tool_id: count_list
    in:
      input1: random_lines/out_file1
""",
                test_data="""
input1:
  value: 1.bed
  type: File
""",
                history_id=history_id,
                wait=True,
            )
            assert "0\n" == self.dataset_populator.get_history_dataset_content(history_id)

    def test_subworkflow_map_over_data_column(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_workflow(
                """class: GalaxyWorkflow
inputs:
  input:
    collection_type: list
outputs:
  reduced:
    outputSource: list:list reduction/out_file1
steps:
  subworkflow:
    in:
      input collection:
        source: input
      input dataset:
        source: input
    run:
      class: GalaxyWorkflow
      inputs:
        input dataset:
          type: data
        input collection:
          collection_type: list
      outputs:
        subworkflow_out:
          outputSource: join out/out_file1
      steps:
        join out:
          tool_id: comp1
          tool_state:
            field1: '1'
            field2: '1'
          in:
            input1:
              source: input dataset
            input2:
              source: input collection
  list:list reduction:
    tool_id: cat_list
    in:
      input1:
        source: subworkflow/subworkflow_out
test_data:
  input:
    collection_type: list
    elements:
      - identifier: 1
        content: A  1
        ext: tabular
      - identifier: 2
        content: B  2
        ext: tabular
""",
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )

    @skip_without_tool("implicit_conversion_format_input")
    def test_run_with_implicit_collection_map_over(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  collection: collection
steps:
  map_over:
    tool_id: implicit_conversion_format_input
    in:
      input1: collection
test_data:
  collection:
    collection_type: list
    elements:
      - identifier: 1
        value: 1.fasta.gz
        type: File
""",
                history_id=history_id,
                assert_ok=True,
            )

    @skip_without_tool("random_lines1")
    def test_change_datatype_collection_map_over(self):
        with self.dataset_populator.test_history() as history_id:
            jobs_summary = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  text_input1: collection
steps:
  map_over:
    tool_id: random_lines1
    in:
      input: text_input1
    outputs:
        out_file1:
          change_datatype: csv
""",
                test_data="""
text_input1:
  collection_type: "list:paired"
""",
                history_id=history_id,
            )
            hdca = self.dataset_populator.get_history_collection_details(history_id=jobs_summary.history_id, hid=4)
            assert hdca["collection_type"] == "list:paired"
            assert len(hdca["elements"][0]["object"]["elements"]) == 2
            forward, reverse = hdca["elements"][0]["object"]["elements"]
            assert forward["object"]["file_ext"] == "csv"
            assert reverse["object"]["file_ext"] == "csv"

    @skip_without_tool("collection_split_on_column")
    def test_change_datatype_discovered_outputs(self):
        with self.dataset_populator.test_history() as history_id:
            jobs_summary = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input: data
steps:
  split:
    tool_id: collection_split_on_column
    in:
      input1: input
    outputs:
        split_output:
          change_datatype: csv
outputs:
  output:
    outputSource: split/split_output
test_data:
  input: "1\t2\t3"
""",
                history_id=history_id,
            )
            inv = self.workflow_populator.get_invocation(jobs_summary.invocation_id, step_details=True)
            details = self.dataset_populator.get_history_collection_details(
                history_id=history_id, content_id=inv["output_collections"]["output"]["id"]
            )
            assert details["elements"][0]["object"]["file_ext"] == "csv"

    @skip_without_tool("collection_type_source_map_over")
    def test_mapping_and_subcollection_mapping(self):
        with self.dataset_populator.test_history() as history_id:
            jobs_summary = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  text_input1: collection
steps:
  map_over:
    tool_id: collection_type_source_map_over
    in:
      input_collect: text_input1
""",
                test_data="""
text_input1:
  collection_type: "list:paired"
""",
                history_id=history_id,
            )
            hdca = self.dataset_populator.get_history_collection_details(history_id=jobs_summary.history_id, hid=1)
            assert hdca["collection_type"] == "list:paired"
            assert len(hdca["elements"][0]["object"]["elements"]) == 2

    @skip_without_tool("empty_list")
    @skip_without_tool("count_multi_file")
    @skip_without_tool("random_lines1")
    def test_empty_list_reduction(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_workflow(
                """
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
        $link: empty_list/output
      seed_source:
        seed_source_selector: set_seed
        seed: asdf
  count_multi_file:
    tool_id: count_multi_file
    in:
      input1: random_lines/out_file1
""",
                test_data="""
input1:
  value: 1.bed
  type: File
""",
                history_id=history_id,
                wait=True,
                round_trip_format_conversion=True,
            )
            assert "0\n" == self.dataset_populator.get_history_dataset_content(history_id)

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

            self._delete(f"histories/{history_id}")

            invocation_cancelled = self._wait_for_invocation_state(uploaded_workflow_id, invocation_id, "cancelled")
            workflow_details = self._invocation_details(uploaded_workflow_id, invocation_id)
            assert len(workflow_details["messages"]) == 1
            message = workflow_details["messages"][0]
            assert message["history_id"] == history_id
            assert message["reason"] == "history_deleted"

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

            self._delete(f"histories/{history_id}")

            invocation_cancelled = self._wait_for_invocation_state(uploaded_workflow_id, invocation_id, "cancelled")
            assert invocation_cancelled, "Workflow state is not cancelled..."
            workflow_details = self._invocation_details(uploaded_workflow_id, invocation_id)
            assert len(workflow_details["messages"]) == 1
            message = workflow_details["messages"][0]
            assert message["history_id"] == history_id
            assert message["reason"] == "history_deleted"

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
            invocation_scheduled = self._wait_for_invocation_state(uploaded_workflow_id, invocation_id, "scheduled")
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
            invocation_cancelled = self._wait_for_invocation_state(uploaded_workflow_id, invocation_id, "cancelled")
            workflow_details = self._invocation_details(uploaded_workflow_id, invocation_id)
            assert len(workflow_details["messages"]) == 1
            message = workflow_details["messages"][0]
            assert "workflow_step_id" in message
            assert message["reason"] == "cancelled_on_review"
            assert invocation_cancelled, "Workflow state is not cancelled..."

    @skip_without_tool("head")
    def test_workflow_map_reduce_pause(self):
        with self.dataset_populator.test_history() as history_id:
            workflow = self.workflow_populator.load_workflow_from_resource("test_workflow_map_reduce_pause")
            uploaded_workflow_id = self.workflow_populator.create_workflow(workflow)
            hda1 = self.dataset_populator.new_dataset(history_id, content="reviewed\nunreviewed")
            fetch_response = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["1\n2\n3", "4\n5\n6"]
            ).json()
            hdca1 = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
            index_map = {
                "0": self._ds_entry(hda1),
                "1": self._ds_entry(hdca1),
            }
            invocation_id = self.__invoke_workflow(uploaded_workflow_id, inputs=index_map, history_id=history_id)

            # Wait for at least one scheduling step.
            self._wait_for_invocation_non_new(uploaded_workflow_id, invocation_id)

            # Make sure the history didn't enter a failed state in there.
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            # Assert the workflow hasn't finished scheduling, we can be pretty sure we
            # are at the pause step in this case then.
            self._assert_invocation_non_terminal(uploaded_workflow_id, invocation_id)

            self.__review_paused_steps(uploaded_workflow_id, invocation_id, order_index=4, action=True)
            self.workflow_populator.wait_for_invocation_and_jobs(history_id, uploaded_workflow_id, invocation_id)
            invocation = self._invocation_details(uploaded_workflow_id, invocation_id)
            assert invocation["state"] == "scheduled"
            assert "reviewed\n1\nreviewed\n4\n" == self.dataset_populator.get_history_dataset_content(history_id)

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

            invocation_url = self._api_url(f"workflows/{uploaded_workflow_id}/usage/{invocation_id}", use_key=True)
            delete_response = delete(invocation_url)
            self._assert_status_code_is(delete_response, 200)
            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id=history_id,
                workflow_id=uploaded_workflow_id,
                invocation_id=invocation_id,
                assert_ok=False,
            )
            invocation = self._invocation_details(uploaded_workflow_id, invocation_id)
            assert invocation["state"] == "cancelled"
            message = invocation["messages"][0]
            assert message["reason"] == "user_request"

    @skip_without_tool("collection_creates_dynamic_nested")
    def test_cancel_workflow_invocation_deletes_jobs(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  list_input:
    type: collection
    collection_type: list
steps:
  first_step:
    tool_id: cat_data_and_sleep
    in:
      input1: list_input
    state:
      sleep_time: 60
  subworkflow_step:
    run:
      class: GalaxyWorkflow
      inputs:
        list_input:
          type: collection
          collection_type: list
      steps:
        intermediate_step:
          tool_id: identifier_multiple
          in:
            input1: list_input
      subworkflow:
    in:
      list_input: first_step/out_file1
test_data:
  list_input:
    collection_type: list
    elements:
      - identifier: 1
        content: A
      - identifier: 2
        content: B
""",
                history_id=history_id,
                wait=False,
            )
            # wait_for_invocation just waits until scheduling complete, not jobs or subworkflow invocations
            self.workflow_populator.wait_for_invocation("null", summary.invocation_id, assert_ok=True)
            invocation_before_cancellation = self.workflow_populator.get_invocation(summary.invocation_id)
            assert invocation_before_cancellation["state"] == "scheduled"
            subworkflow_invocation_id = invocation_before_cancellation["steps"][2]["subworkflow_invocation_id"]
            self.workflow_populator.cancel_invocation(summary.invocation_id)
            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id=history_id,
                workflow_id=summary.workflow_id,
                invocation_id=summary.invocation_id,
                assert_ok=False,
            )
            invocation_jobs = self.workflow_populator.get_invocation_jobs(summary.invocation_id)
            for job in invocation_jobs:
                assert job["state"] == "deleted"
            subworkflow_invocation_jobs = self.workflow_populator.get_invocation_jobs(subworkflow_invocation_id)
            for job in subworkflow_invocation_jobs:
                assert job["state"] == "deleted"

    def test_workflow_failed_output_not_found(self, history_id):
        summary = self._run_workflow(
            """
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
  first_cat1:
    tool_id: cat
    in:
      input1: create_2/does_not_exist
 """,
            history_id=history_id,
            assert_ok=False,
            wait=True,
        )
        invocation = self.workflow_populator.get_invocation(summary.invocation_id)
        assert invocation["state"] == "failed"
        assert len(invocation["messages"]) == 1
        message = invocation["messages"][0]
        assert message["reason"] == "output_not_found"
        assert message["workflow_step_id"] == 1
        assert message["dependent_workflow_step_id"] == 0

    def test_workflow_warning_workflow_output_not_found(self, history_id):
        summary = self._run_workflow(
            """
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
outputs:
  main_out:
    outputSource: create_2/does_not_exist
 """,
            history_id=history_id,
            assert_ok=False,
            wait=True,
        )
        invocation = self.workflow_populator.get_invocation(summary.invocation_id)
        assert invocation["state"] == "scheduled"
        assert len(invocation["messages"]) == 1
        message = invocation["messages"][0]
        assert message["reason"] == "workflow_output_not_found"
        assert "workflow_step_id" in message
        assert message["output_name"] == "does_not_exist"

    @skip_without_tool("__APPLY_RULES__")
    @skip_without_tool("job_properties")
    def test_workflow_failed_input_not_ok(self, history_id):
        summary = self._run_workflow(
            """
class: GalaxyWorkflow
steps:
  job_props:
    tool_id: job_properties
    state:
      thebool: true
      failbool: true
  apply:
    tool_id: __APPLY_RULES__
    in:
      input: job_props/list_output
    state:
      rules:
        rules:
          - type: add_column_metadata
            value: identifier0
        mapping:
          - type: list_identifiers
            columns: [0]
        """,
            history_id=history_id,
            assert_ok=False,
            wait=True,
        )
        invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
        assert invocation_details["state"] == "failed"
        assert len(invocation_details["messages"]) == 1
        message = invocation_details["messages"][0]
        assert message["reason"] == "dataset_failed"
        assert message["workflow_step_id"] == 1

    @skip_without_tool("__RELABEL_FROM_FILE__")
    def test_workflow_failed_with_message_exception(self, history_id):
        summary = self._run_workflow(
            """
class: GalaxyWorkflow
inputs:
  input_collection:
    collection_type: list
    type: collection
  relabel_file:
    type: data
steps:
  relabel:
    tool_id: __RELABEL_FROM_FILE__
    in:
      input: input_collection
      how|labels: relabel_file
test_data:
  input_collection:
    collection_type: "list:list"
  relabel_file:
    value: 1.bed
    type: File
        """,
            history_id=history_id,
            assert_ok=False,
            wait=True,
        )
        invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
        assert invocation_details["state"] == "failed"
        assert len(invocation_details["messages"]) == 1
        message = invocation_details["messages"][0]
        assert message["reason"] == "unexpected_failure"
        assert message["workflow_step_id"] == 2
        assert "Invalid new collection identifier" in message["details"]

    @skip_without_tool("identifier_multiple")
    def test_invocation_map_over(self, history_id):
        summary = self._run_workflow(
            """
class: GalaxyWorkflow
inputs:
  input_collection:
    collection_type: list
    type: collection
outputs:
  main_out:
    outputSource: subworkflow/sub_out
steps:
  subworkflow:
    in:
      data_input: input_collection
    run:
      class: GalaxyWorkflow
      inputs:
        data_input:
          type: data
      outputs:
        sub_out:
          outputSource: output_step/output1
      steps:
        intermediate_step:
          tool_id: identifier_multiple
          in:
            input1: data_input
        output_step:
          tool_id: identifier_multiple
          in:
            input1: intermediate_step/output1
test_data:
  input_collection:
    collection_type: list
    elements:
      - identifier: 1
        content: A
      - identifier: 2
        content: B
        """,
            history_id=history_id,
            assert_ok=True,
            wait=True,
        )
        invocation = self.workflow_populator.get_invocation(summary.invocation_id)
        # For consistency and conditional subworkflow steps this really needs to remain
        # a collection and not get reduced.
        assert "main_out" in invocation["output_collections"], invocation
        hdca_details = self.dataset_populator.get_history_collection_details(history_id)
        assert hdca_details["collection_type"] == "list"
        elements = hdca_details["elements"]
        assert len(elements) == 2
        assert elements[0]["element_identifier"] == "1"
        assert elements[0]["element_type"] == "hda"
        hda_id = elements[0]["object"]["id"]
        hda_content = self.dataset_populator.get_history_dataset_content(history_id, content_id=hda_id)
        assert hda_content.strip() == "1"

    @skip_without_tool("identifier_multiple")
    def test_invocation_map_over_inner_collection(self, history_id):
        summary = self._run_workflow(
            """
class: GalaxyWorkflow
inputs:
  input_collection:
    collection_type: list:list
    type: collection
outputs:
  main_out:
    outputSource: subworkflow/sub_out
steps:
  subworkflow:
    in:
      list_input: input_collection
    run:
      class: GalaxyWorkflow
      inputs:
        list_input:
          type: collection
          collection_type: list
      outputs:
        sub_out:
          outputSource: output_step/output1
      steps:
        intermediate_step:
          tool_id: identifier_multiple
          in:
            input1: list_input
        output_step:
          tool_id: identifier_multiple
          in:
            input1: intermediate_step/output1
test_data:
  input_collection:
    collection_type: list:list
        """,
            history_id=history_id,
            assert_ok=True,
            wait=True,
        )
        invocation = self.workflow_populator.get_invocation(summary.invocation_id)
        assert "main_out" in invocation["output_collections"], invocation
        input_hdca_details = self.dataset_populator.get_history_collection_details(
            history_id, content_id=invocation["inputs"]["0"]["id"]
        )
        assert input_hdca_details["collection_type"] == "list:list"
        assert len(input_hdca_details["elements"]) == 1
        assert input_hdca_details["elements"][0]["element_identifier"] == "test_level_1"
        hdca_details = self.dataset_populator.get_history_collection_details(
            history_id, content_id=invocation["output_collections"]["main_out"]["id"]
        )
        assert hdca_details["collection_type"] == "list"
        elements = hdca_details["elements"]
        assert len(elements) == 1
        assert elements[0]["element_identifier"] == "test_level_1"
        assert elements[0]["element_type"] == "hda"

    @skip_without_tool("identifier_multiple")
    def test_invocation_map_over_inner_collection_with_tool_collection_input(self, history_id):
        summary = self._run_workflow(
            """
class: GalaxyWorkflow
inputs:
  input_collection:
    collection_type: list:list
    type: collection
outputs:
  main_out:
    outputSource: subworkflow/sub_out
steps:
  subworkflow:
    in:
      list_input: input_collection
    run:
      class: GalaxyWorkflow
      inputs:
        list_input:
          type: collection
          collection_type: list
      outputs:
        sub_out:
          outputSource: output_step/output1
      steps:
        output_step:
          tool_id: identifier_all_collection_types
          in:
            input1: list_input
test_data:
  input_collection:
    collection_type: list:list
        """,
            history_id=history_id,
            assert_ok=True,
            wait=True,
        )
        invocation = self.workflow_populator.get_invocation(summary.invocation_id)
        assert "main_out" in invocation["output_collections"], invocation
        input_hdca_details = self.dataset_populator.get_history_collection_details(
            history_id, content_id=invocation["inputs"]["0"]["id"]
        )
        assert input_hdca_details["collection_type"] == "list:list"
        assert len(input_hdca_details["elements"]) == 1
        assert input_hdca_details["elements"][0]["element_identifier"] == "test_level_1"
        hdca_details = self.dataset_populator.get_history_collection_details(
            history_id, content_id=invocation["output_collections"]["main_out"]["id"]
        )
        assert hdca_details["collection_type"] == "list"
        elements = hdca_details["elements"]
        assert len(elements) == 1
        assert elements[0]["element_identifier"] == "test_level_1"
        assert elements[0]["element_type"] == "hda"

    @skip_without_tool("cat")
    def test_pause_outputs_with_deleted_inputs(self):
        self._deleted_inputs_workflow(purge=False)

    @skip_without_tool("cat")
    def test_error_outputs_with_purged_inputs(self):
        self._deleted_inputs_workflow(purge=True)

    def _deleted_inputs_workflow(self, purge):
        # We run a workflow on a collection with a deleted element.
        with self.dataset_populator.test_history() as history_id:
            workflow_id = self._upload_yaml_workflow(
                """
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
"""
            )
            DELETED = 0
            PAUSED_1 = 1
            PAUSED_2 = 2
            fetch_response = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=[("sample1-1", "1 2 3")], wait=True
            ).json()
            hdca1 = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
            deleted_id = hdca1["elements"][DELETED]["object"]["id"]
            self.dataset_populator.delete_dataset(
                history_id=history_id, content_id=deleted_id, purge=purge, wait_for_purge=True
            )
            label_map = {"input1": self._ds_entry(hdca1)}
            workflow_request = dict(
                history=f"hist_id={history_id}",
                ds_map=self.workflow_populator.build_ds_map(workflow_id, label_map),
            )
            r = self.workflow_populator.invoke_workflow_raw(workflow_id, workflow_request)
            self._assert_status_code_is(r, 200)
            invocation_id = r.json()["id"]
            # If this starts failing we may have prevented running workflows on collections with deleted members,
            # in which case we can disable this test.
            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id=history_id, workflow_id=workflow_id, invocation_id=invocation_id, assert_ok=False
            )
            contents = self.__history_contents(history_id)
            datasets = [content for content in contents if content["history_content_type"] == "dataset"]
            assert datasets[DELETED]["deleted"]
            state = "error" if purge else "paused"
            assert datasets[PAUSED_1]["state"] == state
            assert datasets[PAUSED_2]["state"] == "paused"

    def test_run_with_implicit_connection(self):
        with self.dataset_populator.test_history() as history_id:
            run_summary = self._run_workflow(
                """
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
""",
                test_data={"test_input": "hello world"},
                history_id=history_id,
                wait=False,
                round_trip_format_conversion=True,
            )
            history_id = run_summary.history_id
            workflow_id = run_summary.workflow_id
            invocation_id = run_summary.invocation_id
            # Wait for first two jobs to be scheduled - upload and first cat.
            wait_on(lambda: len(self._history_jobs(history_id)) >= 2 or None, "history jobs")
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            invocation = self._invocation_details(workflow_id, invocation_id)
            assert invocation["state"] != "scheduled", invocation
            # Expect two jobs - the upload and first cat. randomlines shouldn't run
            # it is implicitly dependent on second cat.
            self._assert_history_job_count(history_id, 2)

            self.__review_paused_steps(workflow_id, invocation_id, order_index=2, action=True)
            self.workflow_populator.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)
            self._assert_history_job_count(history_id, 4)

    def test_run_with_optional_data_specified_to_multi_data(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_workflow(
                WORKFLOW_OPTIONAL_TRUE_INPUT_DATA,
                test_data="""
input1:
  value: 1.bed
  type: File
""",
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )
            content = self.dataset_populator.get_history_dataset_content(history_id)
            assert "CCDS989.1_cds_0_0_chr1_147962193_r" in content

    def test_run_with_optional_data_unspecified_to_multi_data(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                WORKFLOW_OPTIONAL_TRUE_INPUT_DATA, test_data={}, history_id=history_id, wait=True, assert_ok=True
            )
            content = self.dataset_populator.get_history_dataset_content(history_id)
            assert "No input selected" in content

    def test_run_with_optional_data_unspecified_survives_delayed_step(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_workflow(
                WORKFLOW_OPTIONAL_INPUT_DELAYED_SCHEDULING,
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )

    def test_run_subworkflow_with_optional_data_unspecified(self):
        with self.dataset_populator.test_history() as history_id:
            subworkflow = yaml.safe_load(
                """
class: GalaxyWorkflow
inputs:
  required: data
steps:
  nested_workflow:
    in:
      required: required
test_data:
  required:
    value: 1.bed
    type: File
"""
            )
            subworkflow["steps"]["nested_workflow"]["run"] = yaml.safe_load(WORKFLOW_OPTIONAL_INPUT_DELAYED_SCHEDULING)
            self._run_workflow(
                subworkflow,
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )

    def test_run_with_non_optional_data_unspecified_fails_invocation(self):
        with self.dataset_populator.test_history() as history_id:
            error = self._run_jobs(
                WORKFLOW_OPTIONAL_FALSE_INPUT_DATA,
                test_data={},
                history_id=history_id,
                wait=False,
                assert_ok=False,
                expected_response=400,
            )
            self._assert_failed_on_non_optional_input(error, "input1")

    def test_run_with_optional_collection_specified(self):
        with self.dataset_populator.test_history() as history_id:
            result = self._run_workflow(
                WORKFLOW_OPTIONAL_TRUE_INPUT_COLLECTION,
                test_data="""
input1:
  collection_type: paired
  name: the_dataset_pair
  elements:
    - identifier: forward
      value: 1.fastq
      type: File
    - identifier: reverse
      value: 1.fastq
      type: File
""",
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )
            content = self.dataset_populator.get_history_dataset_content(history_id)
            assert "GAATTGATCAGGACATAGGACAACTGTAGGCACCAT" in content

            invocation_id = result.invocation_id
            request = self.workflow_populator.invocation_to_request(invocation_id)
            assert request["history_id"] == history_id
            assert request["inputs"]["input1"]["src"] == "hdca"
            assert request["inputs"]["input1"]["id"]

    def test_run_with_optional_collection_unspecified(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                WORKFLOW_OPTIONAL_TRUE_INPUT_COLLECTION, test_data={}, history_id=history_id, wait=True, assert_ok=True
            )
            content = self.dataset_populator.get_history_dataset_content(history_id)
            assert "No input specified." in content

    def test_run_with_non_optional_collection_unspecified_fails_invocation(self):
        with self.dataset_populator.test_history() as history_id:
            error = self._run_jobs(
                WORKFLOW_OPTIONAL_FALSE_INPUT_COLLECTION,
                test_data={},
                history_id=history_id,
                wait=False,
                assert_ok=False,
                expected_response=400,
            )
            self._assert_failed_on_non_optional_input(error, "input1")

    def _assert_failed_on_non_optional_input(self, error, input_name):
        assert "err_msg" in error
        err_msg = error["err_msg"]
        assert input_name in err_msg
        assert "is not optional and no input" in err_msg

    def test_run_with_validated_parameter_connection_optional(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_workflow(
                """
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
""",
                test_data="""
text_input:
  value: "abd"
  type: raw
""",
                history_id=history_id,
                wait=True,
                round_trip_format_conversion=True,
            )
            jobs = self._history_jobs(history_id)
            assert len(jobs) == 1

    def test_run_with_int_parameter(self):
        with self.dataset_populator.test_history() as history_id:
            failed = False
            try:
                self._run_jobs(
                    WORKFLOW_PARAMETER_INPUT_INTEGER_REQUIRED,
                    test_data="""
data_input:
  value: 1.bed
  type: File
""",
                    history_id=history_id,
                    wait=True,
                    assert_ok=True,
                )
            except AssertionError as e:
                assert "(int_input) is not optional" in str(e)
                failed = True
            assert failed
            run_response = self._run_workflow(
                WORKFLOW_PARAMETER_INPUT_INTEGER_REQUIRED,
                test_data="""
data_input:
  value: 1.bed
  type: File
int_input:
  value: 1
  type: raw
""",
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )
            # self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            content = self.dataset_populator.get_history_dataset_content(history_id)
            assert len(content.splitlines()) == 1, content
            invocation_id = run_response.invocation_id
            invocation = self.workflow_populator.get_invocation(invocation_id)
            assert invocation["input_step_parameters"]["int_input"]["parameter_value"] == 1

            request = self.workflow_populator.invocation_to_request(invocation_id)
            assert request["history_id"] == history_id
            assert request["inputs"]["int_input"] == 1

            run_response = self._run_workflow(
                WORKFLOW_PARAMETER_INPUT_INTEGER_OPTIONAL,
                test_data="""
data_input:
  value: 1.bed
  type: File
""",
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )
            invocation = self.workflow_populator.get_invocation(run_response.invocation_id)
            # Optional step parameter without default value will not be recorded.
            assert "int_input" not in invocation["input_step_parameters"]

    def test_run_with_int_parameter_nested(self):
        with self.dataset_populator.test_history() as history_id:
            workflow = self.workflow_populator.load_workflow_from_resource("test_subworkflow_with_integer_input")
            workflow_id = self.workflow_populator.create_workflow(workflow)
            hda: dict = self.dataset_populator.new_dataset(history_id, content="1 2 3")
            workflow_request = {
                "history_id": history_id,
                "inputs_by": "name",
                "inputs": json.dumps(
                    {
                        "input_dataset": {"src": "hda", "id": hda["id"]},
                        "int_parameter": 1,
                    }
                ),
            }
            self.workflow_populator.invoke_workflow_and_wait(workflow_id, request=workflow_request)

    def test_run_with_validated_parameter_connection_default_values(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                WORKFLOW_PARAMETER_INPUT_INTEGER_DEFAULT,
                test_data="""
data_input:
  value: 1.bed
  type: File
""",
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            content = self.dataset_populator.get_history_dataset_content(history_id)
            assert len(content.splitlines()) == 3, content

    def test_run_with_default_file_dataset_input(self):
        with self.dataset_populator.test_history() as history_id:
            run_response = self._run_workflow(
                WORKFLOW_WITH_DEFAULT_FILE_DATASET_INPUT,
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )
            invocation_details = self.workflow_populator.get_invocation(run_response.invocation_id, step_details=True)
            assert invocation_details["steps"][0]["outputs"]["output"]["src"] == "hda"
            dataset_details = self.dataset_populator.get_history_dataset_details(
                history_id, dataset_id=invocation_details["steps"][1]["outputs"]["out_file1"]["id"]
            )
            assert dataset_details["file_ext"] == "txt"
            assert "chr1" in dataset_details["peek"]

    def test_run_with_default_file_dataset_input_and_explicit_input(self):
        with self.dataset_populator.test_history() as history_id:
            run_response = self._run_workflow(
                WORKFLOW_WITH_DEFAULT_FILE_DATASET_INPUT,
                test_data="""
default_file_input:
  value: 1.fasta
  type: File
""",
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )
            invocation_details = self.workflow_populator.get_invocation(run_response.invocation_id, step_details=True)
            assert invocation_details["steps"][0]["outputs"]["output"]["src"] == "hda"
            dataset_details = self.dataset_populator.get_history_dataset_details(
                history_id, dataset_id=invocation_details["steps"][1]["outputs"]["out_file1"]["id"]
            )
            assert dataset_details["file_ext"] == "txt"
            assert (
                "gtttgccatcttttgctgctctagggaatccagcagctgtcaccatgtaaacaagcccaggctagaccaGTTACCCTCATCATCTTAGCTGATAGCCAGCCAGCCACCACAGGCA"
                in dataset_details["peek"]
            )

    def test_run_with_default_file_in_step_inline(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_workflow(
                WORKFLOW_WITH_STEP_DEFAULT_FILE_DATASET_INPUT,
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )
            content = self.dataset_populator.get_history_dataset_content(history_id)
            assert "chr1" in content

    def test_conditional_flat_crossproduct_subworkflow(self):
        parent = yaml.safe_load(
            """
class: GalaxyWorkflow
inputs:
  collection_a: collection
  collection_b: collection
  collection_c: collection
steps:
  subworkflow_step:
    run: null
    in:
      collection_a: collection_a
      collection_b: collection_b
    when: $(false)
  pick_value:
    tool_id: pick_value
    in:
      style_cond|type_cond|pick_from_0|value:
        source: subworkflow_step/output_a
      style_cond|type_cond|pick_from_1|value:
        # we need a collection of same length as fallback,
        # which makes this less intuitive than it could be.
        source: collection_c
    tool_state:
      style_cond:
        pick_style: first
        type_cond:
          param_type: data
          pick_from:
          - value:
            __class__: RuntimeValue
          - value:
            __class__: RuntimeValue
outputs:
  the_output:
    outputSource: pick_value/data_param
test_data:
  collection_a:
    collection_type: list
    elements:
      - identifier: A
        content: A
      - identifier: B
        content: B
  collection_b:
    collection_type: list
    elements:
      - identifier: C
        content: C
      - identifier: D
        content: D
  collection_c:
    collection_type: list
    elements:
      - identifier: fallbackA
        content: fallbackA
      - identifier: fallbackBB
        content: fallbackB
      - identifier: fallbackC
        content: fallbackC
      - identifier: fallbackD
        content: fallbackD
"""
        )
        parent["steps"]["subworkflow_step"]["run"] = yaml.safe_load(WORKFLOW_FLAT_CROSS_PRODUCT)
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                parent,
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )
            invocation = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            hdca_id = invocation["output_collections"]["the_output"]["id"]
            hdca = self.dataset_populator.get_history_collection_details(
                history_id=history_id,
                content_id=hdca_id,
            )
            # Following assert is what user would expect, but heuristic currently picks first input element as identifier source
            # assert hdca["elements"][0]["element_identifier"] == "fallbackA"
            assert "fallbackA" in hdca["elements"][0]["object"]["peek"]

    def test_run_with_validated_parameter_connection_invalid(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
""",
                test_data="""
text_input:
  value: ""
  type: raw
""",
                history_id=history_id,
                wait=True,
                assert_ok=False,
            )

    def test_run_with_text_input_connection(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
""",
                test_data="""
data_input:
  value: 1.bed
  type: File
text_input:
  value: asdf
  type: raw
""",
                history_id=history_id,
            )

            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            content = self.dataset_populator.get_history_dataset_content(history_id)
            assert "chrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\n" == content

    def test_run_with_numeric_input_connection(self, history_id):
        self._run_jobs(
            """
class: GalaxyWorkflow
steps:
- label: forty_two
  tool_id: expression_forty_two
  state: {}
- label: consume_expression_parameter
  tool_id: cheetah_casting
  state:
    floattest: 3.14
    inttest:
      $link: forty_two/out1
test_data: {}
""",
            history_id=history_id,
        )

        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        content = self.dataset_populator.get_history_dataset_content(history_id)
        lines = content.split("\n")
        assert len(lines) == 4
        str_43 = lines[0]
        str_4point14 = lines[2]
        assert lines[3] == ""
        assert int(str_43) == 43
        assert abs(float(str_4point14) - 4.14) < 0.0001

    @skip_without_tool("create_input_collection")
    def test_workflow_optional_input_text_parameter_reevaluation(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
class: GalaxyWorkflow
inputs:
  text_input:
    type: text
    optional: true
    default: ''
steps:
  create_collection:
    tool_id: create_input_collection
  nested_workflow:
    in:
      inner_input: create_collection/output
      inner_text_input: text_input
    run:
      class: GalaxyWorkflow
      inputs:
        inner_input:
          type: data_collection_input
        inner_text_input:
          type: text
          optional: true
          default: ''
      steps:
        apply:
          tool_id: __APPLY_RULES__
          in:
            input: inner_input
          state:
            rules:
              rules:
                - type: add_column_metadata
                  value: identifier0
              mapping:
                - type: list_identifiers
                  columns: [0]
      echo:
        cat1:
          in:
            input1: apply/output
          outputs:
            out_file1:
              rename: "#{inner_text_input} suffix"
        """,
                history_id=history_id,
            )

    @skip_without_tool("cat1")
    def test_workflow_rerun_with_use_cached_job(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_run")
        # We launch a workflow
        with self.dataset_populator.test_history() as history_id_one, self.dataset_populator.test_history() as history_id_two:
            workflow_request, _, workflow_id = self._setup_workflow_run(workflow, history_id=history_id_one)
            invocation_id = self.workflow_populator.invoke_workflow_and_wait(
                workflow_id, request=workflow_request
            ).json()["id"]
            invocation_1 = self.workflow_populator.get_invocation(invocation_id)
            # We copy the workflow inputs to a new history
            new_workflow_request = workflow_request.copy()
            new_ds_map = json.loads(new_workflow_request["ds_map"])
            for key, input_values in invocation_1["inputs"].items():
                copy_payload = {"content": input_values["id"], "source": "hda", "type": "dataset"}
                copy_response = self._post(f"histories/{history_id_two}/contents", data=copy_payload, json=True).json()
                new_ds_map[key]["id"] = copy_response["id"]
            new_workflow_request["ds_map"] = json.dumps(new_ds_map, sort_keys=True)
            new_workflow_request["history"] = f"hist_id={history_id_two}"
            new_workflow_request["use_cached_job"] = True
            # We run the workflow again, it should not produce any new outputs
            new_workflow_response = self.workflow_populator.invoke_workflow_raw(
                workflow_id, new_workflow_request, assert_ok=True
            ).json()
            invocation_id = new_workflow_response["id"]

            request = self.workflow_populator.invocation_to_request(invocation_id)
            assert request["use_cached_job"] is True

            self.workflow_populator.wait_for_invocation_and_jobs(history_id_two, workflow_id, invocation_id)

            # get_history_dataset_details defaults to last item in history, so since we've done
            # wait_for_invocation_and_jobs - this will be the output of the cat1 job for both histories
            # (the only job in the loaded workflow).
            first_wf_output_hda = self.dataset_populator.get_history_dataset_details(history_id=history_id_one)
            second_wf_output_hda = self.dataset_populator.get_history_dataset_details(history_id=history_id_two)

            first_wf_output = self._get(f"datasets/{first_wf_output_hda['id']}").json()
            second_wf_output = self._get(f"datasets/{second_wf_output_hda['id']}").json()
            assert (
                first_wf_output["file_name"] == second_wf_output["file_name"]
            ), f"first output:\n{first_wf_output}\nsecond output:\n{second_wf_output}"

    @skip_without_tool("cat1")
    @skip_without_tool("identifier_multiple")
    def test_workflow_rerun_with_cached_job_consumes_implicit_hdca(self, history_id: str):
        workflow = """
class: GalaxyWorkflow
inputs:
  collection_input:
    type: data_collection_input
steps:
  map_over:
    tool_id: cat1
    in:
      input1: collection_input
  consume_hdca:
    tool_id: identifier_multiple
    in:
      input1: map_over/out_file1
"""
        workflow_id = self.workflow_populator.upload_yaml_workflow(name="Consume HDCA", yaml_content=workflow)
        hdca1 = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=[("sample1-1", "1 2 3"), ("sample2-1", "7 8 9")]
        ).json()
        hdca1 = self.dataset_collection_populator.wait_for_fetched_collection(hdca1)
        workflow_request = {
            "inputs": json.dumps({"collection_input": self._ds_entry(hdca1)}),
            "history": f"hist_id={history_id}",
            "use_cached_job": True,
            "inputs_by": "name",
        }
        first_invocation_summary = self.workflow_populator.invoke_workflow_and_wait(
            workflow_id, request=workflow_request
        ).json()
        first_invocation = self.workflow_populator.get_invocation(first_invocation_summary["id"], step_details=True)
        final_job_id_first_invocation = first_invocation["steps"][2]["jobs"][0]["id"]
        second_invocation_summary = self.workflow_populator.invoke_workflow_and_wait(
            workflow_id, request=workflow_request
        ).json()
        second_invocation = self.workflow_populator.get_invocation(second_invocation_summary["id"], step_details=True)
        final_job_id_second_invocation = second_invocation["steps"][2]["jobs"][0]["id"]
        final_job = self.dataset_populator.get_job_details(final_job_id_second_invocation, full=True).json()
        assert final_job["copied_from_job_id"] == final_job_id_first_invocation

    @skip_without_tool("cat1")
    def test_nested_workflow_rerun_with_use_cached_job(self):
        with self.dataset_populator.test_history() as history_id_one, self.dataset_populator.test_history() as history_id_two:
            test_data = """
outer_input:
  value: 1.bed
  type: File
"""
            run_jobs_summary = self._run_workflow(
                WORKFLOW_NESTED_SIMPLE, test_data=test_data, history_id=history_id_one
            )
            workflow_id = run_jobs_summary.workflow_id
            workflow_request = run_jobs_summary.workflow_request
            # We copy the inputs to a new history and re-run the workflow
            inputs = json.loads(workflow_request["inputs"])
            dataset_type = inputs["outer_input"]["src"]
            dataset_id = inputs["outer_input"]["id"]
            copy_payload = {"content": dataset_id, "source": dataset_type, "type": "dataset"}
            copy_response = self._post(f"histories/{history_id_two}/contents", data=copy_payload, json=True)
            self._assert_status_code_is(copy_response, 200)
            new_dataset_id = copy_response.json()["id"]
            inputs["outer_input"]["id"] = new_dataset_id
            workflow_request["use_cached_job"] = True
            workflow_request["history"] = f"hist_id={history_id_two}"
            workflow_request["inputs"] = json.dumps(inputs)
            self.workflow_populator.invoke_workflow_and_wait(workflow_id, request=run_jobs_summary.workflow_request)
            # Now make sure that the HDAs in each history point to the same dataset instances
            history_one_contents = self.__history_contents(history_id_one)
            history_two_contents = self.__history_contents(history_id_two)
            assert len(history_one_contents) == len(history_two_contents)
            for i, (item_one, item_two) in enumerate(zip(history_one_contents, history_two_contents)):
                assert (
                    item_one["dataset_id"] == item_two["dataset_id"]
                ), 'Dataset ids should match, but "{}" and "{}" are not the same for History item {}.'.format(
                    item_one["dataset_id"], item_two["dataset_id"], i + 1
                )

    def test_cannot_run_inaccessible_workflow(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_run_cannot_access")
        workflow_request, _, workflow_id = self._setup_workflow_run(workflow)
        with self._different_user():
            run_workflow_response = self._post(f"workflows/{workflow_id}/invocations", data=workflow_request, json=True)
            self._assert_status_code_is(run_workflow_response, 403)

    def test_400_on_invalid_workflow_id(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_run_does_not_exist")
        workflow_request, _, _ = self._setup_workflow_run(workflow)
        run_workflow_response = self._post(f"workflows/{self._random_key()}/invocations", data=workflow_request)
        self._assert_status_code_is(run_workflow_response, 400)

    def test_cannot_run_against_other_users_history(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_run_does_not_exist")
        workflow_request, history_id, workflow_id = self._setup_workflow_run(workflow)
        with self._different_user():
            other_history_id = self.dataset_populator.new_history()
        workflow_request["history"] = f"hist_id={other_history_id}"
        run_workflow_response = self._post(f"workflows/{workflow_id}/invocations", data=workflow_request, json=True)
        self._assert_status_code_is(run_workflow_response, 403)

    def test_cannot_run_workflow_as_anon(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_run_anon_user")
        workflow_request, _, workflow_id = self._setup_workflow_run(workflow)
        with self._different_user(anon=True):
            run_workflow_response = self._post(f"workflows/{workflow_id}/invocations", data=workflow_request, json=True)
            self._assert_status_code_is(run_workflow_response, 403)
            self._assert_error_code_is(run_workflow_response, error_codes.error_codes_by_name["USER_NO_API_KEY"])

    def test_cannot_run_bootstrap_admin_workflow(self):
        workflow = self.workflow_populator.load_workflow(name="test_bootstrap_admin_cannot_run")
        workflow_request, *_ = self._setup_workflow_run(workflow)
        run_workflow_response = self._post("workflows", data=workflow_request, key=self.master_api_key, json=True)
        self._assert_status_code_is(run_workflow_response, 400)

    @skip_without_tool("cat")
    @skip_without_tool("cat_list")
    def test_workflow_run_with_matching_lists(self):
        workflow = self.workflow_populator.load_workflow_from_resource("test_workflow_matching_lists")
        workflow_id = self.workflow_populator.create_workflow(workflow)
        with self.dataset_populator.test_history() as history_id:
            hdca1 = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=[("sample1-1", "1 2 3"), ("sample2-1", "7 8 9")]
            ).json()
            hdca2 = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=[("sample1-2", "4 5 6"), ("sample2-2", "0 a b")]
            ).json()
            hdca1 = self.dataset_collection_populator.wait_for_fetched_collection(hdca1)
            hdca2 = self.dataset_collection_populator.wait_for_fetched_collection(hdca2)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            label_map = {"list1": self._ds_entry(hdca1), "list2": self._ds_entry(hdca2)}
            workflow_request = dict(
                ds_map=self.workflow_populator.build_ds_map(workflow_id, label_map),
            )
            self.workflow_populator.invoke_workflow_and_wait(
                workflow_id, history_id=history_id, request=workflow_request
            )
            assert "1 2 3\n4 5 6\n7 8 9\n0 a b\n" == self.dataset_populator.get_history_dataset_content(history_id)

    def test_workflow_stability(self):
        # Run this index stability test with following command:
        #   ./run_tests.sh test/api/test_workflows.py:TestWorkflowsApi.test_workflow_stability
        num_tests = 1
        for workflow_file in ["test_workflow_topoambigouity", "test_workflow_topoambigouity_auto_laidout"]:
            workflow = self.workflow_populator.load_workflow_from_resource(workflow_file)
            last_step_map = self._step_map(workflow)
            for _ in range(num_tests):
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
        self._assert_error_code_is(response, error_codes.error_codes_by_name["USER_REQUEST_MISSING_PARAMETER"])

    def test_invalid_create_multiple_types(self):
        data = {"shared_workflow_id": "1234567890abcdef", "from_history_id": "1234567890abcdef"}
        response = self._post("workflows", data)
        self._assert_status_code_is(response, 400)
        self._assert_error_code_is(response, error_codes.error_codes_by_name["USER_REQUEST_INVALID_PARAMETER"])

    @skip_without_tool("cat1")
    def test_run_with_pja(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_pja_run", add_pja=True)
        workflow_request, history_id, workflow_id = self._setup_workflow_run(workflow, inputs_by="step_index")
        workflow_request["replacement_params"] = dumps(dict(replaceme="was replaced"))
        run_workflow_response = self.workflow_populator.invoke_workflow_raw(
            workflow_id, workflow_request, assert_ok=True
        )
        invocation_id = run_workflow_response.json()["id"]
        self.workflow_populator.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id, assert_ok=True)
        content = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=True)
        assert content["name"] == "foo was replaced"

        request = self.workflow_populator.invocation_to_request(invocation_id)
        assert request["replacement_params"]["replaceme"] == "was replaced"

    @skip_without_tool("hidden_param")
    def test_hidden_param_in_workflow(self):
        with self.dataset_populator.test_history() as history_id:
            run_object = self._run_workflow(
                """
class: GalaxyWorkflow
steps:
  step1:
    tool_id: hidden_param
""",
                test_data={},
                history_id=history_id,
                wait=False,
            )
            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id, run_object.workflow_id, run_object.invocation_id
            )
            contents = self.__history_contents(history_id)
            assert len(contents) == 1
            okay_dataset = contents[0]
            assert okay_dataset["state"] == "ok"
            content = self.dataset_populator.get_history_dataset_content(history_id, hid=1)
            assert content == "1\n"

    @skip_without_tool("output_filter")
    def test_optional_workflow_output(self):
        with self.dataset_populator.test_history() as history_id:
            run_object = self._run_workflow(
                """
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
      filter_text_1: 'foo'
      produce_collection: False
""",
                test_data={},
                history_id=history_id,
                wait=False,
            )
            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id, run_object.workflow_id, run_object.invocation_id
            )
            contents = self.__history_contents(history_id)
            assert len(contents) == 1
            okay_dataset = contents[0]
            assert okay_dataset["state"] == "ok"

    @skip_without_tool("output_filter_with_input_optional")
    def test_workflow_optional_input_filtering(self):
        with self.dataset_populator.test_history() as history_id:
            test_data = """
input1:
  collection_type: list
  elements:
    - identifier: A
      content: A
"""
            run_object = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input1:
    type: collection
    collection_type: list
outputs:
  wf_output_1:
    outputSource: output_filter/out_1
steps:
  output_filter:
    tool_id: output_filter_with_input_optional
    in:
      input_1: input1
""",
                test_data=test_data,
                history_id=history_id,
                wait=False,
            )
            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id, run_object.workflow_id, run_object.invocation_id
            )
            contents = self.__history_contents(history_id)
            assert len(contents) == 4
            for content in contents:
                if content["history_content_type"] == "dataset":
                    assert content["state"] == "ok"
                else:
                    print(content)
                    assert content["populated_state"] == "ok"

    @skip_without_tool("cat")
    def test_run_rename_on_mapped_over_collection(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
""",
                test_data="""
input1:
  collection_type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
""",
                history_id=history_id,
            )
            content = self.dataset_populator.get_history_dataset_details(history_id, hid=4, wait=True, assert_ok=True)
            name = content["name"]
            assert name == "my new name", name
            assert content["history_content_type"] == "dataset"
            content = self.dataset_populator.get_history_collection_details(
                history_id, hid=3, wait=True, assert_ok=True
            )
            name = content["name"]
            assert content["history_content_type"] == "dataset_collection", content
            assert name == "my new name", name

    @skip_without_tool("cat")
    def test_run_rename_based_on_inputs_on_mapped_over_collection(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
""",
                test_data="""
input1:
  collection_type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
""",
                history_id=history_id,
            )
            content = self.dataset_populator.get_history_collection_details(
                history_id, hid=3, wait=True, assert_ok=True
            )
            name = content["name"]
            assert content["history_content_type"] == "dataset_collection", content
            assert name == "the_dataset_list suffix", name

    @skip_without_tool("collection_creates_pair")
    def test_run_rename_collection_output(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
""",
                test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
""",
                history_id=history_id,
            )
            details1 = self.dataset_populator.get_history_collection_details(
                history_id, hid=4, wait=True, assert_ok=True
            )
            assert details1["elements"][0]["object"]["visible"] is False
            assert details1["name"] == "my new name", details1
            assert details1["history_content_type"] == "dataset_collection"

    @skip_without_tool("__BUILD_LIST__")
    def test_run_build_list_hide_collection_output(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  - tool_id: __BUILD_LIST__
    in:
      datasets_0|input: input1
    state:
      datasets:
      - id_cond:
          id_select: id
    outputs:
      output:
        hide: true
""",
                test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
""",
                history_id=history_id,
            )
            details1 = self.dataset_populator.get_history_collection_details(
                history_id, hid=3, wait=True, assert_ok=True
            )
            assert details1["elements"][0]["object"]["visible"] is False
            assert details1["name"] == "dataset 1 (as list)", details1
            assert details1["visible"] is False

    @skip_without_tool("__BUILD_LIST__")
    def test_run_build_list_delete_intermediate_collection_output(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  - tool_id: __BUILD_LIST__
    in:
      datasets_0|input: input1
    state:
      datasets:
      - id_cond:
          id_select: id
    outputs:
      output:
        delete_intermediate_datasets: true
""",
                test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
""",
                history_id=history_id,
            )
            details1 = self.dataset_populator.get_history_collection_details(
                history_id, hid=3, wait=True, assert_ok=True
            )
            assert details1["elements"][0]["object"]["visible"] is False
            assert details1["name"] == "dataset 1 (as list)", details1
            # FIXME: this doesn't work because the workflow is still being scheduled
            # TODO: Implement a way to run PJAs that couldn't be run during/after the job
            # after the workflow has run to completion
            assert details1["deleted"] is False

    @skip_without_tool("__BUILD_LIST__")
    def test_run_build_list_change_datatype_collection_output(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  - tool_id: __BUILD_LIST__
    in:
      datasets_0|input: input1
    state:
      datasets:
      - id_cond:
          id_select: idx
    outputs:
      output:
        change_datatype: txt
  - tool_id: __BUILD_LIST__
    in:
      datasets_0|input: input1
    state:
      datasets:
      - id_cond:
          id_select: idx
""",
                test_data="""
input1:
  value: 1.fasta
  type: File
  file_type: fasta
  name: fasta1
""",
                history_id=history_id,
            )
            details1 = self.dataset_populator.get_history_collection_details(
                history_id, hid=3, wait=True, assert_ok=True
            )
            assert details1["name"] == "dataset 1 (as list)", details1
            assert details1["elements"][0]["object"]["visible"] is False
            assert details1["elements"][0]["object"]["file_ext"] == "txt"
            details2 = self.dataset_populator.get_history_collection_details(
                history_id, hid=5, wait=True, assert_ok=True
            )
            # Also check that we don't overwrite the original HDA's datatype
            assert details2["elements"][0]["object"]["file_ext"] == "fasta"

    @skip_without_tool("__EXTRACT_DATASET__")
    def test_run_build_list_change_datatype_new_metadata_file_parameter(self):
        # Regression test for changing datatype to a datatype with a MetadataFileParameter
        with self.dataset_populator.test_history() as history_id:
            self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  build_list:
    tool_id: __BUILD_LIST__
    in:
      datasets_0|input: input1
  extract_dataset:
    tool_id: __EXTRACT_DATASET__
    in:
      input: build_list/output
    outputs:
      output:
        change_datatype: vcf_bgzip
""",
                test_data="""
input1:
  value: test.vcf.gz
  type: File
  file_type: vcf_bgzip
""",
                history_id=history_id,
                assert_ok=True,
                wait=True,
            )

    @skip_without_tool("__BUILD_LIST__")
    def test_run_build_list_rename_collection_output(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  - tool_id: __BUILD_LIST__
    in:
      datasets_0|input: input1
    state:
      datasets:
      - id_cond:
          id_select: idx
    outputs:
      output:
        rename: "my new name"
""",
                test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
""",
                history_id=history_id,
            )
            details1 = self.dataset_populator.get_history_collection_details(
                history_id, hid=3, wait=True, assert_ok=True
            )
            assert details1["elements"][0]["object"]["visible"] is False
            assert details1["name"] == "my new name", details1
            assert details1["history_content_type"] == "dataset_collection"

    @skip_without_tool("create_2")
    def test_run_rename_multiple_outputs(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
""",
                test_data={},
                history_id=history_id,
            )
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
            self._run_jobs(
                """
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
""",
                test_data="""
input1:
  value: 1.fasta
  type: File
  name: fail
""",
                history_id=history_id,
                wait=True,
                assert_ok=False,
            )
            content = self.dataset_populator.get_history_dataset_details(history_id, hid=2, wait=True, assert_ok=False)
            name = content["name"]
            assert content["state"] == "error", content
            input1 = self.dataset_populator.get_history_dataset_details(history_id, hid=1, wait=True, assert_ok=False)
            job_id = content["creating_job"]
            inputs = {
                "input1": {"values": [{"src": "hda", "id": input1["id"]}]},
                "failbool": "false",
                "rerun_remap_job_id": job_id,
            }
            self.dataset_populator.run_tool(
                tool_id="fail_identifier",
                inputs=inputs,
                history_id=history_id,
            )
            unpaused_dataset = self.dataset_populator.get_history_dataset_details(
                history_id, wait=True, assert_ok=False
            )
            assert unpaused_dataset["state"] == "ok"
            assert unpaused_dataset["name"] == f"{name} suffix"

    @skip_without_tool("cat")
    def test_run_rename_based_on_input_recursive(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
""",
                test_data="""
input1:
  value: 1.fasta
  type: File
  name: '#{input1}'
""",
                history_id=history_id,
            )
            content = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=True)
            name = content["name"]
            assert name == "#{input1} #{INPUT1} suffix", name

    @skip_without_tool("cat")
    def test_run_rename_based_on_input_repeat(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
""",
                test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
input2:
  value: 1.fasta
  type: File
  name: fasta2
""",
                history_id=history_id,
            )
            content = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=True)
            name = content["name"]
            assert name == "fasta2 suffix", name

    @skip_without_tool("mapper2")
    def test_run_rename_based_on_input_conditional(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
        rename: "#{fastq_input.fastq_input1 | basename} suffix"
""",
                test_data="""
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
""",
                history_id=history_id,
            )
            content = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=True)
            name = content["name"]
            assert name == "fastq1 suffix", name

    @skip_without_tool("mapper2")
    def test_run_rename_based_on_input_conditional_legacy_pja_reference(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
        # The fully prefixed variant test in "test_run_rename_based_on_input_conditional" should be preferred,
        # but we don't want to break old workflow renaming actions
        rename: "#{fastq_input1 | basename} suffix"
""",
                test_data="""
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
""",
                history_id=history_id,
            )
            content = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=True)
            name = content["name"]
            assert name == "fastq1 suffix", name

    @skip_without_tool("collection_creates_pair")
    def test_run_hide_on_collection_output(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
""",
                test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
""",
                history_id=history_id,
            )
            details1 = self.dataset_populator.get_history_collection_details(
                history_id, hid=4, wait=True, assert_ok=True
            )

            assert details1["history_content_type"] == "dataset_collection"
            assert not details1["visible"], details1

    @skip_without_tool("cat")
    def test_run_hide_on_mapped_over_collection(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
""",
                test_data="""
input1:
  collection_type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
""",
                history_id=history_id,
            )

            content = self.dataset_populator.get_history_dataset_details(history_id, hid=4, wait=True, assert_ok=True)
            assert content["history_content_type"] == "dataset"
            assert not content["visible"]

            content = self.dataset_populator.get_history_collection_details(
                history_id, hid=3, wait=True, assert_ok=True
            )
            assert content["history_content_type"] == "dataset_collection", content
            assert not content["visible"]

    @skip_without_tool("cat")
    def test_tag_auto_propagation(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
""",
                test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
""",
                history_id=history_id,
                round_trip_format_conversion=True,
            )

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
            self._run_jobs(
                """
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
""",
                test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
""",
                history_id=history_id,
                round_trip_format_conversion=True,
            )
            details1 = self.dataset_populator.get_history_collection_details(
                history_id, hid=4, wait=True, assert_ok=True
            )

            assert details1["history_content_type"] == "dataset_collection"
            assert details1["tags"][0] == "name:foo", details1

    @skip_without_tool("cat")
    def test_run_add_tag_on_mapped_over_collection(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
""",
                test_data="""
input1:
  collection_type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
""",
                history_id=history_id,
                round_trip_format_conversion=True,
            )
            details1 = self.dataset_populator.get_history_collection_details(
                history_id, hid=3, wait=True, assert_ok=True
            )

            assert details1["history_content_type"] == "dataset_collection"
            assert details1["tags"][0] == "name:foo", details1

    @skip_without_tool("collection_creates_pair")
    @skip_without_tool("cat")
    def test_run_remove_tag_on_collection_output(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
      input1: first_cat/out_file1
    outputs:
      paired_output:
        remove_tags:
          - "name:foo"
""",
                test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
""",
                history_id=history_id,
                round_trip_format_conversion=True,
            )
            details_dataset_with_tag = self.dataset_populator.get_history_dataset_details(
                history_id, hid=2, wait=True, assert_ok=True
            )

            assert details_dataset_with_tag["history_content_type"] == "dataset", details_dataset_with_tag
            assert details_dataset_with_tag["tags"][0] == "name:foo", details_dataset_with_tag

            details_collection_without_tag = self.dataset_populator.get_history_collection_details(
                history_id, hid=5, wait=True, assert_ok=True
            )
            assert (
                details_collection_without_tag["history_content_type"] == "dataset_collection"
            ), details_collection_without_tag
            assert len(details_collection_without_tag["tags"]) == 0, details_collection_without_tag

    @skip_without_tool("collection_creates_pair")
    @skip_without_tool("cat")
    def test_run_add_tag_on_database_operation_output(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
class: GalaxyWorkflow
inputs:
  input1: data_collection
steps:
  extrat:
    tool_id: __EXTRACT_DATASET__
    in:
      input: input1
    outputs:
      output:
        add_tags:
          - "name:foo"
""",
                test_data="""
input1:
  collection_type: list
  name: the_dataset_list
  elements:
    - identifier: el1
      value: 1.fastq
      type: File
""",
                history_id=history_id,
                round_trip_format_conversion=True,
            )
            details_dataset_with_tag = self.dataset_populator.get_history_dataset_details(
                history_id, hid=3, wait=True, assert_ok=True
            )

            assert details_dataset_with_tag["history_content_type"] == "dataset", details_dataset_with_tag
            assert details_dataset_with_tag["tags"][0] == "name:foo", details_dataset_with_tag

    @skip_without_tool("cat1")
    def test_run_with_runtime_pja(self):
        workflow = self.workflow_populator.load_workflow(name="test_for_pja_runtime")
        uuid0, uuid1, uuid2 = str(uuid4()), str(uuid4()), str(uuid4())
        workflow["steps"]["0"]["uuid"] = uuid0
        workflow["steps"]["1"]["uuid"] = uuid1
        workflow["steps"]["2"]["uuid"] = uuid2
        workflow_request, history_id, workflow_id = self._setup_workflow_run(workflow, inputs_by="step_index")
        workflow_request["replacement_params"] = dumps(dict(replaceme="was replaced"))
        pja_map = {
            "RenameDatasetActionout_file1": dict(
                action_type="RenameDatasetAction",
                output_name="out_file1",
                action_arguments=dict(newname="foo ${replaceme}"),
            )
        }
        workflow_request["parameters"] = dumps({uuid2: {"__POST_JOB_ACTIONS__": pja_map}})

        self.workflow_populator.invoke_workflow_and_wait(workflow_id, request=workflow_request)
        content = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=True)
        assert content["name"] == "foo was replaced", content["name"]

        # Test for regression of previous behavior where runtime post job actions
        # would be added to the original workflow post job actions.
        downloaded_workflow = self._download_workflow(workflow_id)
        pjas = list(downloaded_workflow["steps"]["2"]["post_job_actions"].values())
        assert len(pjas) == 0, len(pjas)

    @skip_without_tool("cat1")
    def test_run_with_delayed_runtime_pja(self):
        workflow_id = self._upload_yaml_workflow(
            """
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
""",
            round_trip_format_conversion=True,
        )
        downloaded_workflow = self._download_workflow(workflow_id)
        uuid_dict = {int(index): step["uuid"] for index, step in downloaded_workflow["steps"].items()}
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="1 2 3")
            self.dataset_populator.wait_for_history(history_id)
            inputs = {
                "0": self._ds_entry(hda),
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
            workflow_request["parameters"] = dumps({uuid2: {"__POST_JOB_ACTIONS__": pja_map}})
            invocation_id = self.__invoke_workflow(
                workflow_id, inputs=inputs, request=workflow_request, history_id=history_id
            )

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
            self._run_jobs(
                """
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
""",
                test_data={"input1": "hello world"},
                history_id=history_id,
            )
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

    @skip_without_tool("cat1")
    def test_validated_post_job_action_validated(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
    post_job_actions:
      ValidateOutputsAction:
        action_type: ValidateOutputsAction
""",
                test_data={"input1": {"type": "File", "file_type": "fastqsanger", "value": "1.fastqsanger"}},
                history_id=history_id,
            )
            hda2 = self.dataset_populator.get_history_dataset_details(history_id, hid=2)
            assert hda2["validated_state"] == "ok"

    @skip_without_tool("cat1")
    def test_validated_post_job_action_unvalidated_default(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                WORKFLOW_SIMPLE,
                test_data={"input1": {"type": "File", "file_type": "fastqsanger", "value": "1.fastqsanger"}},
                history_id=history_id,
            )
            hda2 = self.dataset_populator.get_history_dataset_details(history_id, hid=2)
            assert hda2["validated_state"] == UNKNOWN

    @skip_without_tool("cat1")
    def test_validated_post_job_action_invalid(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
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
    post_job_actions:
      ValidateOutputsAction:
        action_type: ValidateOutputsAction
""",
                test_data={"input1": {"type": "File", "file_type": "fastqcssanger", "value": "1.fastqsanger"}},
                history_id=history_id,
            )
            hda2 = self.dataset_populator.get_history_dataset_details(history_id, hid=2)
            assert hda2["validated_state"] == "invalid"

    def test_value_restriction_with_select_and_text_param(self):
        workflow_id = self.workflow_populator.upload_yaml_workflow(
            """
class: GalaxyWorkflow
inputs:
  select_text:
     type: text
     restrictOnConnections: true
steps:
  select:
    tool_id: multi_select
    in:
      select_ex: select_text
  tool_with_text_input:
    tool_id: param_text_option
    in:
      text_param: select_text
"""
        )
        with self.dataset_populator.test_history() as history_id:
            run_workflow = self._download_workflow(workflow_id, style="run", history_id=history_id)
        options = run_workflow["steps"][0]["inputs"][0]["options"]
        assert len(options) == 5
        assert options[0] == ["Ex1", "--ex1", False]

    def test_value_restriction_with_select_from_subworkflow_input(self):
        workflow_id = self.workflow_populator.upload_yaml_workflow(
            """
class: GalaxyWorkflow
inputs:
  Outer input parameter:
    optional: false
    restrictOnConnections: true
    type: string
steps:
- in:
    inner input parameter:
      source: Outer input parameter
  run:
    class: GalaxyWorkflow
    label: Restriction from subworkflow param
    inputs:
      inner input parameter:
        optional: false
        restrictOnConnections: true
        type: string
    steps:
    - tool_id: multi_select
      in:
        select_ex:
          source: inner input parameter
"""
        )
        with self.dataset_populator.test_history() as history_id:
            run_workflow = self._download_workflow(workflow_id, style="run", history_id=history_id)
        options = run_workflow["steps"][0]["inputs"][0]["options"]
        assert len(options) == 5
        assert options[0] == ["Ex1", "--ex1", False]

    @skip_without_tool("random_lines1")
    def test_run_replace_params_by_tool(self):
        workflow_request, history_id, workflow_id = self._setup_random_x2_workflow("test_for_replace_tool_params")
        workflow_request["parameters"] = dumps(dict(random_lines1=dict(num_lines=5)))
        self.workflow_populator.invoke_workflow_and_wait(workflow_id, request=workflow_request)
        # Would be 8 and 6 without modification
        self.__assert_lines_hid_line_count_is(history_id, 2, 5)
        self.__assert_lines_hid_line_count_is(history_id, 3, 5)

    @skip_without_tool("random_lines1")
    def test_run_replace_params_by_uuid(self):
        workflow_request, history_id, workflow_id = self._setup_random_x2_workflow("test_for_replace_")
        workflow_request["parameters"] = dumps(
            {
                "58dffcc9-bcb7-4117-a0e1-61513524b3b1": dict(num_lines=4),
                "58dffcc9-bcb7-4117-a0e1-61513524b3b2": dict(num_lines=3),
            }
        )
        self.workflow_populator.invoke_workflow_and_wait(workflow_id, request=workflow_request)
        # Would be 8 and 6 without modification
        self.__assert_lines_hid_line_count_is(history_id, 2, 4)
        self.__assert_lines_hid_line_count_is(history_id, 3, 3)

    @skip_without_tool("cat1")
    @skip_without_tool("addValue")
    def test_run_batch(self):
        workflow = self.workflow_populator.load_workflow_from_resource("test_workflow_batch")
        workflow_id = self.workflow_populator.create_workflow(workflow)
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3", wait=True)
            hda2 = self.dataset_populator.new_dataset(history_id, content="4 5 6", wait=True)
            hda3 = self.dataset_populator.new_dataset(history_id, content="7 8 9", wait=True)
            hda4 = self.dataset_populator.new_dataset(history_id, content="10 11 12", wait=True)
            parameters = {
                "0": {
                    "input": {
                        "batch": True,
                        "values": [
                            {"id": hda1.get("id"), "hid": hda1.get("hid"), "src": "hda"},
                            {"id": hda2.get("id"), "hid": hda2.get("hid"), "src": "hda"},
                            {"id": hda3.get("id"), "hid": hda2.get("hid"), "src": "hda"},
                            {"id": hda4.get("id"), "hid": hda2.get("hid"), "src": "hda"},
                        ],
                    }
                },
                "1": {
                    "input": {"batch": False, "values": [{"id": hda1.get("id"), "hid": hda1.get("hid"), "src": "hda"}]},
                    "exp": "2",
                },
            }
            workflow_request = {
                "history_id": history_id,
                "batch": True,
                "parameters_normalized": True,
                "parameters": dumps(parameters),
            }
            invocation_response = self._post(f"workflows/{workflow_id}/usage", data=workflow_request, json=True)
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
            assert r1 == t1
            assert r2 == t2
            assert r3 == t3
            assert r4 == t4

    @skip_without_tool("cat1")
    @skip_without_tool("addValue")
    def test_run_batch_inputs(self):
        workflow = self.workflow_populator.load_workflow_from_resource("test_workflow_batch")
        workflow_id = self.workflow_populator.create_workflow(workflow)
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
            hda2 = self.dataset_populator.new_dataset(history_id, content="4 5 6")
            hda3 = self.dataset_populator.new_dataset(history_id, content="7 8 9")
            hda4 = self.dataset_populator.new_dataset(history_id, content="10 11 12")
            inputs = {
                "coolinput": {
                    "batch": True,
                    "values": [
                        {"id": hda1.get("id"), "hid": hda1.get("hid"), "src": "hda"},
                        {"id": hda2.get("id"), "hid": hda2.get("hid"), "src": "hda"},
                        {"id": hda3.get("id"), "hid": hda2.get("hid"), "src": "hda"},
                        {"id": hda4.get("id"), "hid": hda2.get("hid"), "src": "hda"},
                    ],
                }
            }
            parameters = {
                "1": {
                    "input": {"batch": False, "values": [{"id": hda1.get("id"), "hid": hda1.get("hid"), "src": "hda"}]},
                    "exp": "2",
                }
            }
            workflow_request = {
                "history_id": history_id,
                "batch": True,
                "inputs": dumps(inputs),
                "inputs_by": "name",
                "parameters_normalized": True,
                "parameters": dumps(parameters),
            }
            invocation_response = self._post(f"workflows/{workflow_id}/usage", data=workflow_request, json=True)
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
            assert r1 == t1
            assert r2 == t2
            assert r3 == t3
            assert r4 == t4

    @skip_without_tool("validation_default")
    def test_parameter_substitution_sanitization(self):
        substitions = dict(input1='" ; echo "moo')
        run_workflow_response, history_id = self._run_validation_workflow_with_substitions(substitions)

        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        assert "__dq__ X echo __dq__moo\n" == self.dataset_populator.get_history_dataset_content(history_id, hid=1)

    @skip_without_tool("validation_repeat")
    def test_parameter_substitution_validation_value_errors_0(self):
        with self.dataset_populator.test_history() as history_id:
            workflow_id = self._upload_yaml_workflow(
                """
class: GalaxyWorkflow
steps:
  validation:
    tool_id: validation_repeat
    state:
      r2:
        - text: "abd"
"""
            )
            workflow_request = dict(
                history=f"hist_id={history_id}", parameters=dumps(dict(validation_repeat={"r2_0|text": ""}))
            )
            url = f"workflows/{workflow_id}/invocations"
            invocation_response = self._post(url, data=workflow_request, json=True)
            # Take a valid stat and make it invalid, assert workflow won't run.
            self._assert_status_code_is(invocation_response, 400)

    @skip_without_tool("collection_paired_test")
    def test_run_map_over_with_step_parameter_dict(self):
        # Tests what the legacy run form submits
        with self.dataset_populator.test_history() as history_id:
            hdca = self.dataset_collection_populator.create_list_of_pairs_in_history(history_id).json()["outputs"][0]
            workflow_id = self._upload_yaml_workflow(
                """
class: GalaxyWorkflow
steps:
  "0":
    tool_id: collection_paired_conditional_structured_like
    state:
      cond:
        input1:
          __class__: RuntimeValue
"""
            )
            workflow_request = {
                "history": f"hist_id={history_id}",
                "parameters": dumps({"0": {"cond|input1": {"values": [{"id": hdca["id"], "src": "hdca"}]}}}),
                "parameters_normalized": True,
            }
            url = f"workflows/{workflow_id}/invocations"
            invocation_response = self._post(url, data=workflow_request, json=True)
            invocation_response.raise_for_status()
            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id=history_id, workflow_id=workflow_id, invocation_id=invocation_response.json()["id"]
            )

    @skip_without_tool("validation_default")
    def test_parameter_substitution_validation_value_errors_1(self):
        substitions = dict(select_param='" ; echo "moo')
        run_workflow_response, history_id = self._run_validation_workflow_with_substitions(substitions)

        self._assert_status_code_is(run_workflow_response, 400)

    @skip_without_tool("validation_repeat")
    def test_workflow_import_state_validation_1(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_jobs(
                """
class: GalaxyWorkflow
steps:
  validation:
    tool_id: validation_repeat
    state:
      r2:
      - text: ""
""",
                history_id=history_id,
                wait=False,
                expected_response=400,
                assert_ok=False,
            )

    def _run_validation_workflow_with_substitions(self, substitions):
        workflow = self.workflow_populator.load_workflow_from_resource("test_workflow_validation_1")
        uploaded_workflow_id = self.workflow_populator.create_workflow(workflow)
        history_id = self.dataset_populator.new_history()
        workflow_request = dict(
            history=f"hist_id={history_id}",
            workflow_id=uploaded_workflow_id,
            parameters=dumps(dict(validation_default=substitions)),
        )
        run_workflow_response = self.workflow_populator.invoke_workflow_raw(uploaded_workflow_id, workflow_request)
        return run_workflow_response, history_id

    def test_subworkflow_import_order_maintained(self, history_id):
        summary = self._run_workflow(
            """
class: GalaxyWorkflow
inputs:
  outer_input_1:
    type: int
    default: 1
    position:
      left: 0
      top: 0
  outer_input_2:
    type: int
    default: 2
    position:
      left: 100
      top: 0
steps:
  nested_workflow:
    in:
      inner_input_1: outer_input_1
      inner_input_2: outer_input_2
    run:
      class: GalaxyWorkflow
      inputs:
        inner_input_1:
          type: int
          position:
            left: 100
            top: 0
        inner_input_2:
          type: int
          position:
            left: 0
            top: 0
      steps: []
      outputs:
        - label: nested_out_1
          outputSource: inner_input_1/output
        - label: nested_out_2
          outputSource: inner_input_2/output
outputs:
  - label: out_1
    outputSource: nested_workflow/nested_out_1
  - label: out_2
    outputSource: nested_workflow/nested_out_2
""",
            history_id=history_id,
            assert_ok=False,
            wait=False,
        )
        self.workflow_populator.wait_for_invocation(summary.workflow_id, summary.invocation_id)
        self.workflow_populator.wait_for_history_workflows(
            summary.history_id, assert_ok=False, expected_invocation_count=2
        )
        invocation = self.workflow_populator.get_invocation(summary.invocation_id)
        output_values = invocation["output_values"]
        assert output_values["out_1"] == 1
        assert output_values["out_2"] == 2

    @skip_without_tool("random_lines1")
    def test_run_replace_params_by_steps(self):
        workflow_request, history_id, workflow_id, steps = self._setup_random_x2_workflow_steps(
            "test_for_replace_step_params"
        )
        params = dumps({str(steps[1]["id"]): dict(num_lines=5)})
        workflow_request["parameters"] = params
        self.workflow_populator.invoke_workflow_and_wait(workflow_id, request=workflow_request)
        # Would be 8 and 6 without modification
        self.__assert_lines_hid_line_count_is(history_id, 2, 8)
        self.__assert_lines_hid_line_count_is(history_id, 3, 5)

    @skip_without_tool("random_lines1")
    def test_run_replace_params_nested(self):
        workflow_request, history_id, workflow_id, steps = self._setup_random_x2_workflow_steps(
            "test_for_replace_step_params_nested"
        )
        seed_source = dict(
            seed_source_selector="set_seed",
            seed="moo",
        )
        params = dumps(
            {
                str(steps[0]["id"]): dict(num_lines=1, seed_source=seed_source),
                str(steps[1]["id"]): dict(num_lines=1, seed_source=seed_source),
            }
        )
        workflow_request["parameters"] = params
        self.workflow_populator.invoke_workflow_and_wait(workflow_id, request=workflow_request)
        assert "2\n" == self.dataset_populator.get_history_dataset_content(history_id)

    @skip_without_tool("random_lines1")
    def test_run_replace_params_nested_normalized(self):
        workflow_request, history_id, workflow_id, steps = self._setup_random_x2_workflow_steps(
            "test_for_replace_step_normalized_params_nested"
        )
        parameters = {
            "num_lines": 1,
            "seed_source|seed_source_selector": "set_seed",
            "seed_source|seed": "moo",
        }
        params = dumps({str(steps[0]["id"]): parameters, str(steps[1]["id"]): parameters})
        workflow_request["parameters"] = params
        workflow_request["parameters_normalized"] = False
        self.workflow_populator.invoke_workflow_and_wait(workflow_id, request=workflow_request)
        assert "2\n" == self.dataset_populator.get_history_dataset_content(history_id)

    @skip_without_tool("random_lines1")
    def test_run_replace_params_over_default(self):
        with self.dataset_populator.test_history() as history_id:
            wf_run = self._run_workflow(
                WORKFLOW_ONE_STEP_DEFAULT,
                test_data="""
step_parameters:
  '1':
    num_lines: 4
input:
  value: 1.bed
  type: File
""",
                history_id=history_id,
                wait=True,
                assert_ok=True,
                round_trip_format_conversion=True,
            )
            result = self.dataset_populator.get_history_dataset_content(history_id)
            assert result.count("\n") == 4

            request = self.workflow_populator.invocation_to_request(wf_run.invocation_id)
            assert request["parameters"]["1"]["num_lines"] == 4

            self.workflow_populator.rerun(wf_run)
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
            run_summary = self._run_workflow(
                """
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
""",
                test_data="""
step_parameters:
  '3':
    num_lines: 4
input:
  value: 1.bed
  type: File
""",
                history_id=history_id,
                wait=False,
            )
            wait_on(lambda: len(self._history_jobs(history_id)) >= 2 or None, "history jobs")
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            workflow_id = run_summary.workflow_id
            invocation_id = run_summary.invocation_id

            self.__review_paused_steps(workflow_id, invocation_id, order_index=2, action=True)
            self.workflow_populator.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)

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

    def test_invocation_filtering(self):
        with self._different_user(email=f"{uuid4()}@test.com"):
            history_id = self.dataset_populator.new_history()
            # new user, start with no invocations
            assert not self._assert_invocation_for_url_is("invocations")
            self._run_jobs(
                """
class: GalaxyWorkflow
inputs:
  input:
    type: data
    optional: true
steps: []
""",
                history_id=history_id,
                wait=False,
            )
            first_invocation = self._assert_invocation_for_url_is("invocations")
            new_history_id = self.dataset_populator.new_history()
            # new history has no invocations
            assert not self._assert_invocation_for_url_is(f"invocations?history_id={new_history_id}")
            self._run_jobs(
                """
class: GalaxyWorkflow
inputs:
  input:
    type: data
    optional: true
steps: []
""",
                history_id=new_history_id,
                wait=False,
            )
            # new history has one invocation now
            new_invocation = self._assert_invocation_for_url_is(f"invocations?history_id={new_history_id}")
            # filter invocation by workflow instance id
            self._assert_invocation_for_url_is(
                f"invocations?workflow_id={first_invocation['workflow_id']}&instance=true", first_invocation
            )
            # limit to 1, newest invocation first by default
            self._assert_invocation_for_url_is("invocations?limit=1", target_invocation=new_invocation)
            # limit to 1, descending sort on date
            self._assert_invocation_for_url_is(
                "invocations?limit=1&sort_by=create_time&sort_desc=true", target_invocation=new_invocation
            )
            # limit to 1, ascending sort on date
            self._assert_invocation_for_url_is(
                "invocations?limit=1&sort_by=create_time&sort_desc=false", target_invocation=first_invocation
            )
            # limit to 1, ascending sort on date, offset 1
            self._assert_invocation_for_url_is(
                "invocations?limit=1&sort_by=create_time&sort_desc=false&offset=1", target_invocation=new_invocation
            )

    def _assert_invocation_for_url_is(self, route, target_invocation=None):
        response = self._get(route)
        self._assert_status_code_is(response, 200)
        invocations = response.json()
        if target_invocation:
            assert len(invocations) == 1
            assert invocations[0]["id"] == target_invocation["id"]
        if invocations:
            assert len(invocations) == 1
            return invocations[0]

    @skip_without_tool("cat1")
    def test_only_own_invocations_indexed_and_accessible(self):
        workflow_id, usage = self._run_workflow_once_get_invocation("test_usage_accessiblity")
        with self._different_user():
            usage_details_response = self._get(f"workflows/{workflow_id}/usage/{usage['id']}")
            self._assert_status_code_is(usage_details_response, 403)
            index_response = self._get(f"workflows/{workflow_id}/invocations")
            self._assert_status_code_is(index_response, 200)
            assert len(index_response.json()) == 0

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
        self._wait_for_invocation_state(workflow_id, invocation_id, "scheduled")
        usage_details = self._invocation_details(workflow_id, invocation_id)

        invocation_steps = usage_details["steps"]
        invocation_input_step, invocation_tool_step = {}, {}
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
        invocation_tool_step_response = self._get(
            f"workflows/{workflow_id}/invocations/{invocation_id}/steps/{invocation_tool_step_id}"
        )
        self._assert_status_code_is(invocation_tool_step_response, 200)
        self._assert_has_keys(invocation_tool_step_response.json(), "id", "order_index", "job_id")

        assert invocation_tool_step_response.json()["job_id"] == job_id

    def test_invocation_with_collection_mapping(self):
        workflow_id, invocation_id = self._run_mapping_workflow()

        usage_details = self._invocation_details(workflow_id, invocation_id)
        # Assert some high-level things about the structure of data returned.
        self._assert_has_keys(usage_details, "inputs", "steps", "workflow_id")

        invocation_steps = usage_details["steps"]
        for step_index, invocation_step in enumerate(invocation_steps):
            self._assert_has_keys(invocation_step, "workflow_step_id", "order_index", "id")
            assert step_index == invocation_step["order_index"]
        invocation_input_step = invocation_steps[0]
        invocation_tool_step = invocation_steps[1]

        # Tool steps have non-null job_ids (deprecated though they may be)
        assert invocation_input_step.get("job_id") is None
        assert invocation_tool_step.get("job_id") is None
        assert invocation_tool_step["state"] == "scheduled"

        usage_details = self._invocation_details(workflow_id, invocation_id, legacy_job_state="true")
        # Assert some high-level things about the structure of data returned.
        self._assert_has_keys(usage_details, "inputs", "steps", "workflow_id")

        invocation_steps = usage_details["steps"]
        assert len(invocation_steps) == 3
        for invocation_step in invocation_steps:
            self._assert_has_keys(invocation_step, "workflow_step_id", "order_index", "id")

        assert invocation_steps[1]["state"] == "ok"

    def test_data_input_recovery_on_delayed_input(self):
        self.workflow_populator.run_workflow(
            """
class: GalaxyWorkflow
inputs: {}
outputs:
  the_output:
    outputSource: child/output
steps:
  running_output:
    tool_id: job_properties
    tool_state:
      failbool: false
      sleepsecs: 3
      thebool: false
  child:
    in:
      input_dataset:
        source: running_output/out_file1
    run:
      class: GalaxyWorkflow
      inputs:
        input_dataset: data
        run_step:
          default: false
          optional: true
          type: boolean
      outputs:
        output:
          outputSource: conditional_cat/out_file1
      steps:
        conditional_cat:
          tool_id: cat
          when: $(inputs.when)
          in:
            input1: input_dataset
            when:
              source: run_step"""
        )

    def test_subworkflow_output_not_found_fails(self):
        # This test might start failing if we ever validate connections before attempting to schedule
        summary = self.workflow_populator.run_workflow(
            """
class: GalaxyWorkflow
inputs:
  input: data
outputs:
  the_output:
    outputSource: child/output
steps:
  child:
    in:
      input_dataset:
        source: input
    run:
      class: GalaxyWorkflow
      inputs:
        input_dataset: data
      outputs:
        output:
          outputSource: cat/out_file_that_doesnt_exist
      steps:
        cat:
          tool_id: cat
          in:
            input1: input_dataset
test_data:
  input:
    value: 1.fasta
    type: File
            """,
            assert_ok=False,
        )
        invocation = self.workflow_populator.get_invocation(summary.invocation_id)
        assert invocation["state"] == "failed"
        assert invocation["messages"][0]["reason"] == "output_not_found"

    def _run_mapping_workflow(self):
        history_id = self.dataset_populator.new_history()
        summary = self._run_workflow(
            """
class: GalaxyWorkflow
inputs:
  input_c: collection
steps:
  cat1:
    tool_id: cat1
    in:
       input1: input_c
""",
            test_data="""
input_c:
  collection_type: list
  elements:
    - identifier: i1
      content: "0"
    - identifier: i2
      content: "1"
""",
            history_id=history_id,
            wait=True,
            assert_ok=True,
        )
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
            workflow_request, history_id, _ = self._setup_workflow_run(workflow_id=other_id)
            response = self._get(f"workflows/{other_id}/usage")
            self._assert_status_code_is(response, 200)
            assert len(response.json()) == 0
            run_workflow_response = self.workflow_populator.invoke_workflow_raw(
                workflow_id, workflow_request, assert_ok=True
            )
            run_workflow_dict = run_workflow_response.json()
            invocation_id = run_workflow_dict["id"]
            usage_details_response = self._get(f"workflows/{other_id}/usage/{invocation_id}")
            self._assert_status_code_is(usage_details_response, 200)

    @skip_without_tool("cat1")
    def test_invocations_accessible_published_workflow(self):
        workflow_id = self.workflow_populator.simple_workflow("test_usage", publish=True)
        with self._different_user():
            workflow_request, history_id, _ = self._setup_workflow_run(workflow_id=workflow_id)
            response = self._get(f"workflows/{workflow_id}/usage")
            self._assert_status_code_is(response, 200)
            assert len(response.json()) == 0
            run_workflow_response = self.workflow_populator.invoke_workflow_raw(
                workflow_id, workflow_request, assert_ok=True
            )
            run_workflow_dict = run_workflow_response.json()
            invocation_id = run_workflow_dict["id"]
            usage_details_response = self._get(f"workflows/{workflow_id}/usage/{invocation_id}")
            self._assert_status_code_is(usage_details_response, 200)

    @skip_without_tool("cat1")
    def test_invocations_not_accessible_by_different_user_for_published_workflow(self):
        workflow_id = self.workflow_populator.simple_workflow("test_usage", publish=True)
        workflow_request, history_id, _ = self._setup_workflow_run(workflow_id=workflow_id)
        response = self._get(f"workflows/{workflow_id}/usage")
        self._assert_status_code_is(response, 200)
        assert len(response.json()) == 0
        run_workflow_response = self.workflow_populator.invoke_workflow_raw(
            workflow_id, workflow_request, assert_ok=True
        )
        run_workflow_dict = run_workflow_response.json()
        invocation_id = run_workflow_dict["id"]
        with self._different_user():
            usage_details_response = self._get(f"workflows/{workflow_id}/usage/{invocation_id}")
            self._assert_status_code_is(usage_details_response, 403)

    def test_invocation_filtering_exclude_subworkflow(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_workflow(
                WORKFLOW_NESTED_SIMPLE,
                test_data="""
outer_input:
  value: 1.bed
  type: File
""",
                history_id=history_id,
            )
            assert len(self.workflow_populator.history_invocations(history_id)) == 2
            assert len(self.workflow_populator.history_invocations(history_id, include_nested_invocations=False)) == 1

    def test_workflow_publishing(self):
        workflow_id = self.workflow_populator.simple_workflow("dummy")
        response = self._show_workflow(workflow_id)
        assert not response["published"]
        assert not response["importable"]
        published_worklow = self._put(f"workflows/{workflow_id}", data={"published": True}, json=True).json()
        assert published_worklow["published"]
        importable_worklow = self._put(f"workflows/{workflow_id}", data={"importable": True}, json=True).json()
        assert importable_worklow["importable"]
        unpublished_worklow = self._put(f"workflows/{workflow_id}", data={"published": False}, json=True).json()
        assert not unpublished_worklow["published"]
        unimportable_worklow = self._put(f"workflows/{workflow_id}", data={"importable": False}, json=True).json()
        assert not unimportable_worklow["importable"]

    def test_workflow_from_path_requires_admin(self):
        # There are two ways to import workflows from paths, just verify both require an admin.
        workflow_directory = mkdtemp()
        try:
            workflow_path = os.path.join(workflow_directory, "workflow.yml")
            with open(workflow_path, "w") as f:
                f.write(WORKFLOW_NESTED_REPLACEMENT_PARAMETER)
            import_response = self.workflow_populator.import_workflow_from_path_raw(workflow_path)
            self._assert_status_code_is(import_response, 403)
            self._assert_error_code_is(import_response, error_codes.error_codes_by_name["ADMIN_REQUIRED"])

            path_as_uri = f"file://{workflow_path}"
            import_data = dict(archive_source=path_as_uri)
            import_response = self._post("workflows", data=import_data)
            self._assert_status_code_is(import_response, 403)
            self._assert_error_code_is(import_response, error_codes.error_codes_by_name["ADMIN_REQUIRED"])
        finally:
            shutil.rmtree(workflow_directory)

    def test_cannot_run_workflow_on_immutable_history(self) -> None:
        with self.dataset_populator.test_history() as history_id:
            # once we purge the history, it becomes immutable
            self._delete(f"histories/{history_id}", data={"purge": True}, json=True)

            with self.assertRaisesRegex(AssertionError, "History is immutable"):
                self.workflow_populator.run_workflow(
                    WORKFLOW_INPUTS_AS_OUTPUTS,
                    test_data={"input1": "hello world", "text_input": {"value": "A text variable", "type": "raw"}},
                    history_id=history_id,
                )

    def _invoke_paused_workflow(self, history_id):
        workflow = self.workflow_populator.load_workflow_from_resource("test_workflow_pause")
        workflow_id = self.workflow_populator.create_workflow(workflow)
        hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
        index_map = {
            "0": self._ds_entry(hda1),
        }
        invocation_id = self.__invoke_workflow(
            workflow_id,
            history_id=history_id,
            inputs=index_map,
        )
        return workflow_id, invocation_id

    def _wait_for_invocation_non_new(self, workflow_id, invocation_id):
        target_state_reached = False
        for _ in range(50):
            invocation = self._invocation_details(workflow_id, invocation_id)
            if invocation["state"] != "new":
                target_state_reached = True
                break

            time.sleep(0.25)

        return target_state_reached

    def _assert_invocation_non_terminal(self, workflow_id, invocation_id):
        invocation = self._invocation_details(workflow_id, invocation_id)
        assert invocation["state"] in ["ready", "new"], invocation

    def _wait_for_invocation_state(self, workflow_id, invocation_id, target_state):
        target_state_reached = False
        for _ in range(25):
            invocation = self._invocation_details(workflow_id, invocation_id)
            if invocation["state"] == target_state:
                target_state_reached = True
                break

            time.sleep(0.5)

        return target_state_reached

    def _update_workflow(self, workflow_id, workflow_object):
        return self.workflow_populator.update_workflow(workflow_id, workflow_object)

    def _invocation_step_details(self, workflow_id, invocation_id, step_id):
        invocation_step_response = self._get(f"workflows/{workflow_id}/usage/{invocation_id}/steps/{step_id}")
        self._assert_status_code_is(invocation_step_response, 200)
        invocation_step_details = invocation_step_response.json()
        return invocation_step_details

    def _execute_invocation_step_action(self, workflow_id, invocation_id, step_id, action):
        raw_url = f"workflows/{workflow_id}/usage/{invocation_id}/steps/{step_id}"
        url = self._api_url(raw_url, use_key=True)
        payload = dumps(dict(action=action))
        action_response = put(url, data=payload)
        self._assert_status_code_is(action_response, 200)
        invocation_step_details = action_response.json()
        return invocation_step_details

    def _setup_random_x2_workflow_steps(self, name: str):
        workflow_request, history_id, workflow_id = self._setup_random_x2_workflow(name)
        random_line_steps = self._random_lines_steps(workflow_request, workflow_id)
        return workflow_request, history_id, workflow_id, random_line_steps

    def _random_lines_steps(self, workflow_request: dict, workflow_id: str):
        workflow_summary_response = self._get(f"workflows/{workflow_id}")
        self._assert_status_code_is(workflow_summary_response, 200)
        steps = workflow_summary_response.json()["steps"]
        return sorted(
            (step for step in steps.values() if step["tool_id"] == "random_lines1"), key=lambda step: step["id"]
        )

    def _setup_random_x2_workflow(self, name: str):
        workflow = self.workflow_populator.load_random_x2_workflow(name)
        uploaded_workflow_id = self.workflow_populator.create_workflow(workflow)
        workflow_inputs = self.workflow_populator.workflow_inputs(uploaded_workflow_id)
        key = next(iter(workflow_inputs.keys()))
        history_id = self.dataset_populator.new_history()
        ten_lines = "\n".join(str(_) for _ in range(10))
        hda1 = self.dataset_populator.new_dataset(history_id, content=ten_lines)
        workflow_request = dict(
            history=f"hist_id={history_id}",
            ds_map=dumps(
                {
                    key: self._ds_entry(hda1),
                }
            ),
        )
        return workflow_request, history_id, uploaded_workflow_id

    def __review_paused_steps(self, uploaded_workflow_id, invocation_id, order_index, action=True):
        invocation = self._invocation_details(uploaded_workflow_id, invocation_id)
        invocation_steps = invocation["steps"]
        pause_steps = [s for s in invocation_steps if s["order_index"] == order_index]
        for pause_step in pause_steps:
            pause_step_id = pause_step["id"]

            self._execute_invocation_step_action(uploaded_workflow_id, invocation_id, pause_step_id, action=action)

    def __assert_lines_hid_line_count_is(self, history, hid, lines):
        contents_url = f"histories/{history}/contents"
        history_contents = self.__history_contents(history)
        hda_summary = next(hc for hc in history_contents if hc["hid"] == hid)
        hda_info_response = self._get(f"{contents_url}/{hda_summary['id']}")
        self._assert_status_code_is(hda_info_response, 200)
        assert hda_info_response.json()["metadata_data_lines"] == lines

    def __history_contents(self, history_id):
        contents_url = f"histories/{history_id}/contents"
        history_contents_response = self._get(contents_url)
        self._assert_status_code_is(history_contents_response, 200)
        return history_contents_response.json()

    def __invoke_workflow(self, *args, **kwds) -> str:
        return self.workflow_populator.invoke_workflow_and_assert_ok(*args, **kwds)

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
        show_response = self._get(f"workflows/{workflow_id}")
        self._assert_status_code_is(show_response, 200)
        return show_response.json()

    def _assert_looks_like_instance_workflow_representation(self, workflow):
        self._assert_has_keys(workflow, "url", "owner", "inputs", "annotation", "steps")
        for step in workflow["steps"].values():
            self._assert_has_keys(
                step,
                "id",
                "type",
                "tool_id",
                "tool_version",
                "annotation",
                "tool_inputs",
                "input_steps",
            )

    def _all_user_invocation_ids(self):
        all_invocations_for_user = self._get("invocations")
        self._assert_status_code_is(all_invocations_for_user, 200)
        invocation_ids = [i["id"] for i in all_invocations_for_user.json()]
        return invocation_ids

    def test_subworkflow_tags(self):
        workflow = self.workflow_populator.load_workflow_from_resource("test_subworkflow_with_tags")
        workflow_id = self.workflow_populator.create_workflow(workflow)
        downloaded_workflow = self._download_workflow(workflow_id)
        subworkflow = downloaded_workflow["steps"]["1"]["subworkflow"]
        assert subworkflow["tags"] == []

    def test_upload_malformated_yaml(self):
        malformated_yaml = "class: GalaxyWorkflow:\n    a-1:()"
        r = self._post("workflows", files={"archive_file": io.StringIO(malformated_yaml)})
        assert r.status_code == 400


class TestAdminWorkflowsApi(BaseWorkflowsApiTestCase):
    require_admin_user = True

    def test_import_export_dynamic_tools(self, history_id):
        workflow_id = self._upload_yaml_workflow(
            """
class: GalaxyWorkflow
steps:
  - type: input
    label: input1
  - tool_id: cat1
    label: first_cat
    state:
      input1:
        $link: 0
  - label: embed1
    run:
      class: GalaxyTool
      command: echo 'hello world 2' > $output1
      outputs:
        output1:
          format: txt
  - tool_id: cat1
    state:
      input1:
        $link: first_cat/out_file1
      queries:
      - input2:
          $link: embed1/output1
test_data:
  input1: "hello world"
"""
        )
        downloaded_workflow = self._download_workflow(workflow_id)
        response = self.workflow_populator.create_workflow_response(downloaded_workflow)
        workflow_id = response.json()["id"]
        hda1 = self.dataset_populator.new_dataset(history_id, content="Hello World Second!")
        workflow_request = dict(
            inputs_by="name",
            inputs=json.dumps({"input1": self._ds_entry(hda1)}),
        )
        self.workflow_populator.invoke_workflow_and_wait(workflow_id, history_id=history_id, request=workflow_request)
        assert self.dataset_populator.get_history_dataset_content(history_id) == "Hello World Second!\nhello world 2\n"
