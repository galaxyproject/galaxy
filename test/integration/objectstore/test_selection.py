"""Integration tests for object stores."""

import os
import string

from galaxy.model import Dataset
from galaxy.model.unittest_utils.store_fixtures import (
    deferred_hda_model_store_dict,
    one_hda_model_store_dict,
)
from ._base import (
    BaseObjectStoreIntegrationTestCase,
    files_count,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "selection_job_conf.xml")
JOB_RESOURCE_PARAMETERS_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "selection_job_resource_parameters_conf.xml")

DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE = string.Template(
    """<?xml version="1.0"?>
<object_store type="distributed" id="primary" order="0">
    <backends>
        <backend id="default" type="disk" weight="1" name="Default Store">
            <description>This is my description of the default store with *markdown*.</description>
            <files_dir path="${temp_directory}/files_default"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_default"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_default"/>
        </backend>
        <backend id="static" type="disk" weight="0">
            <files_dir path="${temp_directory}/files_static"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_static"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_static"/>
        </backend>
        <backend id="dynamic_ebs" type="disk" weight="0">
            <files_dir path="${temp_directory}/files_dynamic_ebs"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_dynamic_ebs"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_dynamic_ebs"/>
        </backend>
        <backend id="dynamic_s3" type="disk" weight="0">
            <files_dir path="${temp_directory}/files_dynamic_s3"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_dynamic_s3"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_dynamic_s3"/>
        </backend>
    </backends>
</object_store>
"""
)


class ObjectStoreSelectionIntegrationTestCase(BaseObjectStoreIntegrationTestCase):
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
        config["job_config_file"] = JOB_CONFIG_FILE
        config["job_resource_params_file"] = JOB_RESOURCE_PARAMETERS_CONFIG_FILE
        config["object_store_store_by"] = "uuid"
        config["metadata_strategy"] = "celery_extended"
        config["outputs_to_working_directory"] = True

    def _object_store_counts(self):
        files_default_count = files_count(self.files_default_path)
        files_static_count = files_count(self.files_static_path)
        files_dynamic_count = files_count(self.files_dynamic_path)
        return files_default_count, files_static_count, files_dynamic_count

    def _assert_file_counts(self, default, static, dynamic_ebs, dynamic_s3):
        files_default_count = files_count(self.files_default_path)
        files_static_count = files_count(self.files_static_path)
        files_dynamic_ebs_count = files_count(self.files_dynamic_ebs_path)
        files_dynamic_s3_count = files_count(self.files_dynamic_s3_path)
        assert default == files_default_count
        assert static == files_static_count
        assert dynamic_ebs == files_dynamic_ebs_count
        assert dynamic_s3 == files_dynamic_s3_count

    def _assert_no_external_filename(self):
        # Should maybe be its own test case ...
        for external_filename_tuple in self._app.model.session.query(Dataset.external_filename).all():
            assert external_filename_tuple[0] is None

    def test_tool_simple_constructs(self):
        with self.dataset_populator.test_history() as history_id:

            def _run_tool(tool_id, inputs):
                self.dataset_populator.run_tool(
                    tool_id,
                    inputs,
                    history_id,
                )
                self.dataset_populator.wait_for_history(history_id)

            self._assert_file_counts(0, 0, 0, 0)

            hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
            self.dataset_populator.wait_for_history(history_id)
            hda1_input = {"src": "hda", "id": hda1["id"]}
            storage_info = self.dataset_populator.dataset_storage_info(hda1["id"])
            assert "Default Store" == storage_info["name"]
            assert "*markdown*" in storage_info["description"]

            # One file uploaded, added to default object store ID.
            self._assert_file_counts(1, 0, 0, 0)

            # should create two files in static object store.
            _run_tool("multi_data_param", {"f1": hda1_input, "f2": hda1_input})
            self._assert_file_counts(1, 2, 0, 0)

            # should create two files in ebs object store.
            create_10_inputs_1 = {
                "input1": hda1_input,
                "input2": hda1_input,
            }
            _run_tool("create_10", create_10_inputs_1)
            self._assert_file_counts(1, 2, 10, 0)

            # should create 10 files in S3 object store.
            create_10_inputs_2 = {
                "__job_resource|__job_resource__select": "yes",
                "__job_resource|how_store": "slow",
                "input1": hda1_input,
                "input2": hda1_input,
            }
            _run_tool("create_10", create_10_inputs_2)
            self._assert_file_counts(1, 2, 10, 10)
            self._assert_no_external_filename()
            assert self._latest_dataset.object_store_id == "dynamic_s3"

            # assure discarded datsets don't have an object store ID populated
            # and don't create files in the object store.
            self.dataset_populator.create_contents_from_store(
                history_id,
                store_dict=one_hda_model_store_dict(),
            )
            self._assert_file_counts(1, 2, 10, 10)
            assert self._latest_dataset.object_store_id is None

            # assure deferred datsets don't have an object store ID populated
            # and don't create files in the object store.
            self.dataset_populator.create_contents_from_store(
                history_id,
                store_dict=deferred_hda_model_store_dict(),
            )
            self._assert_file_counts(1, 2, 10, 10)
            assert self._latest_dataset.object_store_id is None

    @property
    def _latest_dataset(self):
        latest_dataset = self._app.model.session.query(Dataset).order_by(Dataset.table.c.id.desc()).first()
        return latest_dataset
