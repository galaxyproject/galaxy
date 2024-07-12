"""Test selecting an object store with user's preferred object store."""

import os
import string
from typing import (
    Any,
    Dict,
    Optional,
)

from sqlalchemy import select

from galaxy.model import Dataset
from galaxy_test.base.populators import WorkflowPopulator
from galaxy_test.base.workflow_fixtures import (
    WORKFLOW_NESTED_OUTPUT,
    WORKFLOW_NESTED_SIMPLE,
    WORKFLOW_NESTED_TWICE_OUTPUT,
)
from ._base import BaseObjectStoreIntegrationTestCase

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))

DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE = string.Template(
    """<?xml version="1.0"?>
<object_store type="distributed" id="primary" order="0">
    <backends>
        <backend id="default" allow_selection="true" type="disk" weight="1" name="Default Store">
            <description>This is my description of the default store with *markdown*.</description>
            <files_dir path="${temp_directory}/files_default"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_default"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_default"/>
        </backend>
        <backend id="static" allow_selection="true" type="disk" weight="0" name="Static Storage">
            <files_dir path="${temp_directory}/files_static"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_static"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_static"/>
        </backend>
        <backend id="dynamic_ebs" allow_selection="true" type="disk" weight="0" name="Dynamic EBS">
            <quota source="ebs" />
            <files_dir path="${temp_directory}/files_dynamic_ebs"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_dynamic_ebs"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_dynamic_ebs"/>
        </backend>
        <backend id="dynamic_s3" type="disk" weight="0">
            <quota source="s3" />
            <files_dir path="${temp_directory}/files_dynamic_s3"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_dynamic_s3"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_dynamic_s3"/>
        </backend>
    </backends>
</object_store>
"""
)


TEST_WORKFLOW = """
class: GalaxyWorkflow
inputs:
  input1: data
outputs:
  wf_output_1:
    outputSource: second_cat/out_file1
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

TEST_WORKFLOW_TEST_DATA = """
input1:
  value: 1.fasta
  type: File
  name: fasta1
"""

TEST_NESTED_WORKFLOW_TEST_DATA = """
outer_input:
  value: 1.fasta
  type: File
  name: fasta1
"""

# simple output collections
WORKFLOW_WITH_COLLECTIONS_1 = """
class: GalaxyWorkflow
inputs:
  text_input1: data
outputs:
  wf_output_1:
    outputSource: collection_creates_list/list_output
steps:
  cat_inputs:
    tool_id: cat1
    in:
      input1: text_input1
      queries_0|input2: text_input1
  split_up:
    tool_id: collection_split_on_column
    in:
      input1: cat_inputs/out_file1
  collection_creates_list:
    tool_id: collection_creates_list
    in:
      input1: split_up/split_output
"""


# a collection with a dynamic output
WORKFLOW_WITH_COLLECTIONS_2 = """
class: GalaxyWorkflow
inputs:
  text_input1: data
outputs:
  wf_output_1:
    outputSource: collection_creates_list/list_output
  wf_output_2:
    outputSource: split_up/split_output
steps:
  cat_inputs:
    tool_id: cat1
    in:
      input1: text_input1
      queries_0|input2: text_input1
  split_up:
    tool_id: collection_split_on_column
    in:
      input1: cat_inputs/out_file1
  collection_creates_list:
    tool_id: collection_creates_list
    in:
      input1: split_up/split_output
"""


WORKFLOW_WITH_COLLECTIONS_1_TEST_DATA = """
text_input1: |
  samp1\t10.0
  samp2\t20.0
"""


def assert_storage_name_is(storage_dict: Dict[str, Any], name: str):
    storage_name = storage_dict["name"]
    assert name == storage_name, f"Found incorrect storage name {storage_name}, expected {name} in {storage_dict}"


class TestObjectStoreSelectionWithPreferredObjectStoresIntegration(BaseObjectStoreIntegrationTestCase):
    framework_tool_and_types = True

    # populated by config_object_store
    files_default_path: str
    files_static_path: str
    files_dynamic_path: str
    files_dynamic_ebs_path: str
    files_dynamic_s3_path: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_object_store(DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE, config)
        config["object_store_store_by"] = "uuid"
        config["outputs_to_working_directory"] = True

    def setUp(self):
        super().setUp()
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_setting_unselectable_object_store_id_not_allowed(self):
        response = self.dataset_populator.update_user_raw({"preferred_object_store_id": "dynamic_s3"})
        assert response.status_code == 400

    def test_index_query(self):
        selectable_object_store_ids = self.dataset_populator.selectable_object_store_ids()
        assert "default" in selectable_object_store_ids
        assert "static" in selectable_object_store_ids
        assert "dynamic_s3" not in selectable_object_store_ids

    def test_objectstore_selection(self):
        with self.dataset_populator.test_history() as history_id:

            def _run_tool(tool_id, inputs, preferred_object_store_id=None):
                response = self.dataset_populator.run_tool(
                    tool_id,
                    inputs,
                    history_id,
                    preferred_object_store_id=preferred_object_store_id,
                )
                self.dataset_populator.wait_for_history(history_id)
                return response

            self._set_user_preferred_object_store_id("static")

            storage_info, hda1 = self._create_hda_get_storage_info(history_id)
            assert_storage_name_is(storage_info, "Static Storage")

            self._reset_user_preferred_object_store_id()

            storage_info, _ = self._create_hda_get_storage_info(history_id)
            assert_storage_name_is(storage_info, "Default Store")

            self.dataset_populator.update_history(history_id, {"preferred_object_store_id": "static"})
            storage_info, _ = self._create_hda_get_storage_info(history_id)
            assert_storage_name_is(storage_info, "Static Storage")

            hda1_input = {"src": "hda", "id": hda1["id"]}
            response = _run_tool("multi_data_param", {"f1": hda1_input, "f2": hda1_input})
            storage_info = self._storage_info_for_job_output(response)
            assert_storage_name_is(storage_info, "Static Storage")

            hda1_input = {"src": "hda", "id": hda1["id"]}
            response = _run_tool(
                "multi_data_param", {"f1": hda1_input, "f2": hda1_input}, preferred_object_store_id="default"
            )
            storage_info = self._storage_info_for_job_output(response)
            assert_storage_name_is(storage_info, "Default Store")

            self._reset_user_preferred_object_store_id()

    def test_objectstore_selection_dynamic_output_tools(self):
        with self.dataset_populator.test_history() as history_id:

            def _run_tool(tool_id, inputs, preferred_object_store_id=None):
                response = self.dataset_populator.run_tool(
                    tool_id,
                    inputs,
                    history_id,
                    preferred_object_store_id=preferred_object_store_id,
                )
                return response

            self._set_user_preferred_object_store_id("static")
            response = _run_tool("collection_creates_dynamic_list_of_pairs", {"foo": "bar"})
            self.dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
            some_dataset = self.dataset_populator.get_history_dataset_details(history_id)
            storage_dict = self._storage_info(some_dataset)
            assert_storage_name_is(storage_dict, "Static Storage")
            self._reset_user_preferred_object_store_id()

    def test_workflow_objectstore_selection(self):
        with self.dataset_populator.test_history() as history_id:
            output_dict, intermediate_dict = self._run_workflow_get_output_storage_info_dicts(history_id)
            assert_storage_name_is(output_dict, "Default Store")
            assert_storage_name_is(intermediate_dict, "Default Store")

            output_dict, intermediate_dict = self._run_workflow_get_output_storage_info_dicts(
                history_id, {"preferred_object_store_id": "static"}
            )
            assert_storage_name_is(output_dict, "Static Storage")
            assert_storage_name_is(intermediate_dict, "Static Storage")

            output_dict, intermediate_dict = self._run_workflow_get_output_storage_info_dicts(
                history_id,
                {
                    "preferred_outputs_object_store_id": "static",
                    "preferred_intermediate_object_store_id": "dynamic_ebs",
                },
            )
            assert_storage_name_is(output_dict, "Static Storage")
            assert_storage_name_is(intermediate_dict, "Dynamic EBS")

    def test_simple_subworkflow_objectstore_selection(self):
        with self.dataset_populator.test_history() as history_id:
            output_dict, intermediate_dict = self._run_simple_nested_workflow_get_output_storage_info_dicts(
                history_id,
            )
            assert_storage_name_is(output_dict, "Default Store")
            assert_storage_name_is(intermediate_dict, "Default Store")

        with self.dataset_populator.test_history() as history_id:
            output_dict, intermediate_dict = self._run_simple_nested_workflow_get_output_storage_info_dicts(
                history_id, {"preferred_object_store_id": "static"}
            )
            assert_storage_name_is(output_dict, "Static Storage")
            assert_storage_name_is(intermediate_dict, "Static Storage")

    def test_non_effective_subworkflow_outputs_ignored(self):
        with self.dataset_populator.test_history() as history_id:
            output_dict, intermediate_dict = self._run_simple_nested_workflow_get_output_storage_info_dicts(
                history_id,
                {
                    "preferred_outputs_object_store_id": "static",
                    "preferred_intermediate_object_store_id": "dynamic_ebs",
                },
            )
            assert_storage_name_is(output_dict, "Static Storage")
            assert_storage_name_is(intermediate_dict, "Dynamic EBS")

    def test_effective_subworkflow_outputs(self):
        with self.dataset_populator.test_history() as history_id:
            (
                output_dict,
                intermediate_dict,
            ) = self._run_nested_workflow_with_effective_output_get_output_storage_info_dicts(
                history_id,
                {
                    "preferred_outputs_object_store_id": "static",
                    "preferred_intermediate_object_store_id": "dynamic_ebs",
                },
            )
            assert_storage_name_is(output_dict, "Static Storage")
            assert_storage_name_is(intermediate_dict, "Dynamic EBS")

    def test_effective_subworkflow_outputs_twice_nested(self):
        with self.dataset_populator.test_history() as history_id:
            (
                output_dict,
                intermediate_dict,
            ) = self._run_nested_workflow_with_effective_output_get_output_storage_info_dicts(
                history_id,
                {
                    "preferred_outputs_object_store_id": "static",
                    "preferred_intermediate_object_store_id": "dynamic_ebs",
                },
                twice_nested=True,
            )
            assert_storage_name_is(output_dict, "Static Storage")
            assert_storage_name_is(intermediate_dict, "Dynamic EBS")

    def test_workflow_collection(self):
        with self.dataset_populator.test_history() as history_id:
            intermediate_dict, output_info = self._run_workflow_with_collections_1(history_id)
            assert_storage_name_is(intermediate_dict, "Default Store")
            assert_storage_name_is(output_info, "Default Store")

        with self.dataset_populator.test_history() as history_id:
            intermediate_dict, output_info = self._run_workflow_with_collections_1(
                history_id, {"preferred_object_store_id": "static"}
            )
            assert_storage_name_is(intermediate_dict, "Static Storage")
            assert_storage_name_is(output_info, "Static Storage")

    def test_workflow_collection_mixed(self):
        with self.dataset_populator.test_history() as history_id:
            intermediate_dict, output_info = self._run_workflow_with_collections_1(
                history_id,
                {
                    "preferred_outputs_object_store_id": "static",
                    "preferred_intermediate_object_store_id": "dynamic_ebs",
                },
            )
            assert_storage_name_is(output_info, "Static Storage")
            assert_storage_name_is(intermediate_dict, "Dynamic EBS")

    def test_workflow_collection_dynamic_output(self):
        with self.dataset_populator.test_history() as history_id:
            intermediate_dict, output_info = self._run_workflow_with_collections_2(
                history_id,
                {
                    "preferred_outputs_object_store_id": "static",
                    "preferred_intermediate_object_store_id": "dynamic_ebs",
                },
            )
            assert_storage_name_is(output_info, "Static Storage")
            assert_storage_name_is(intermediate_dict, "Dynamic EBS")

    def _run_workflow_with_collections_1(self, history_id: str, extra_invocation_kwds: Optional[Dict[str, Any]] = None):
        wf_run = self.workflow_populator.run_workflow(
            WORKFLOW_WITH_COLLECTIONS_1,
            test_data=WORKFLOW_WITH_COLLECTIONS_1_TEST_DATA,
            history_id=history_id,
            extra_invocation_kwds=extra_invocation_kwds,
        )
        jobs = wf_run.jobs_for_tool("cat1")
        intermediate_info = self._storage_info_for_job_id(jobs[0]["id"])
        list_jobs = wf_run.jobs_for_tool("collection_creates_list")
        assert len(list_jobs) == 1
        output_list_dict = self.dataset_populator.get_job_details(list_jobs[0]["id"], full=True).json()
        output_collections = output_list_dict["output_collections"]
        output_collection = output_collections["list_output"]
        hdca = self.dataset_populator.get_history_collection_details(history_id, content_id=output_collection["id"])
        objects = [e["object"] for e in hdca["elements"]]
        output_info = self._storage_info(objects[0])
        return intermediate_info, output_info

    def _run_workflow_with_collections_2(self, history_id: str, extra_invocation_kwds: Optional[Dict[str, Any]] = None):
        wf_run = self.workflow_populator.run_workflow(
            WORKFLOW_WITH_COLLECTIONS_2,
            test_data=WORKFLOW_WITH_COLLECTIONS_1_TEST_DATA,
            history_id=history_id,
            extra_invocation_kwds=extra_invocation_kwds,
        )
        jobs = wf_run.jobs_for_tool("cat1")
        intermediate_info = self._storage_info_for_job_id(jobs[0]["id"])
        list_jobs = wf_run.jobs_for_tool("collection_split_on_column")
        assert len(list_jobs) == 1
        output_list_dict = self.dataset_populator.get_job_details(list_jobs[0]["id"], full=True).json()
        output_collections = output_list_dict["output_collections"]
        output_collection = output_collections["split_output"]
        hdca = self.dataset_populator.get_history_collection_details(history_id, content_id=output_collection["id"])
        objects = [e["object"] for e in hdca["elements"]]
        output_info = self._storage_info(objects[0])
        return intermediate_info, output_info

    def _run_simple_nested_workflow_get_output_storage_info_dicts(
        self, history_id: str, extra_invocation_kwds: Optional[Dict[str, Any]] = None
    ):
        wf_run = self.workflow_populator.run_workflow(
            WORKFLOW_NESTED_SIMPLE,
            test_data=TEST_NESTED_WORKFLOW_TEST_DATA,
            history_id=history_id,
            extra_invocation_kwds=extra_invocation_kwds,
        )
        jobs = wf_run.jobs_for_tool("cat1")
        print(jobs)
        assert len(jobs) == 2

        output_info = self._storage_info_for_job_id(jobs[0]["id"])
        # nested workflow step... a non-output
        randomlines_jobs = self.dataset_populator.history_jobs_for_tool(history_id, "random_lines1")
        assert len(randomlines_jobs) == 1
        intermediate_info = self._storage_info_for_job_id(randomlines_jobs[0]["id"])
        return output_info, intermediate_info

    def _run_nested_workflow_with_effective_output_get_output_storage_info_dicts(
        self, history_id: str, extra_invocation_kwds: Optional[Dict[str, Any]] = None, twice_nested=False
    ):
        workflow_data = WORKFLOW_NESTED_OUTPUT if not twice_nested else WORKFLOW_NESTED_TWICE_OUTPUT
        wf_run = self.workflow_populator.run_workflow(
            workflow_data,
            test_data=TEST_NESTED_WORKFLOW_TEST_DATA,
            history_id=history_id,
            extra_invocation_kwds=extra_invocation_kwds,
        )
        jobs = wf_run.jobs_for_tool("cat1")
        print(jobs)
        assert len(jobs) == 2

        intermediate_info = self._storage_info_for_job_id(jobs[1]["id"])
        # nested workflow step... a non-output
        randomlines_jobs = self.dataset_populator.history_jobs_for_tool(history_id, "random_lines1")
        assert len(randomlines_jobs) == 1
        output_info = self._storage_info_for_job_id(randomlines_jobs[0]["id"])
        return output_info, intermediate_info

    def _run_workflow_get_output_storage_info_dicts(
        self, history_id: str, extra_invocation_kwds: Optional[Dict[str, Any]] = None
    ):
        wf_run = self.workflow_populator.run_workflow(
            TEST_WORKFLOW,
            test_data=TEST_WORKFLOW_TEST_DATA,
            history_id=history_id,
            extra_invocation_kwds=extra_invocation_kwds,
        )
        jobs = wf_run.jobs_for_tool("cat")
        print(jobs)
        assert len(jobs) == 2
        output_info = self._storage_info_for_job_id(jobs[0]["id"])
        intermediate_info = self._storage_info_for_job_id(jobs[1]["id"])
        return output_info, intermediate_info

    def _storage_info_for_job_id(self, job_id: str) -> Dict[str, Any]:
        job_dict = self.dataset_populator.get_job_details(job_id, full=True).json()
        return self._storage_info_for_job_output(job_dict)

    def _storage_info_for_job_output(self, job_dict) -> Dict[str, Any]:
        outputs = job_dict["outputs"]  # could be a list or dictionary depending on source
        try:
            output = outputs[0]
        except KeyError:
            output = list(outputs.values())[0]
        storage_info = self._storage_info(output)
        return storage_info

    def _storage_info(self, hda):
        return self.dataset_populator.dataset_storage_info(hda["id"])

    def _set_user_preferred_object_store_id(self, store_id: Optional[str]) -> None:
        self.dataset_populator.set_user_preferred_object_store_id(store_id)

    def _reset_user_preferred_object_store_id(self):
        self._set_user_preferred_object_store_id(None)

    def _create_hda_get_storage_info(self, history_id: str):
        hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
        self.dataset_populator.wait_for_history(history_id)
        return self._storage_info(hda1), hda1

    @property
    def _latest_dataset(self):
        latest_dataset = self._app.model.session.scalars(
            select(Dataset).order_by(Dataset.table.c.id.desc()).limit(1)
        ).first()
        return latest_dataset
