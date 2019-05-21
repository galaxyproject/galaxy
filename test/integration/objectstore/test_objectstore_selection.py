"""Integration tests for object stores."""

import os
import string

from base import integration_util  # noqa: I202
from base.populators import (
    DatasetPopulator,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "objectstore_selection_job_conf.xml")
JOB_RESOURCE_PARAMETERS_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "objectstore_selection_job_resource_parameters_conf.xml")

DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE = string.Template("""<?xml version="1.0"?>
<object_store type="distributed" id="primary" order="0">
    <backends>
        <backend id="default" type="disk" weight="1">
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
""")


class ObjectStoreJobsIntegrationTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        temp_directory = cls._test_driver.mkdtemp()
        cls.object_stores_parent = temp_directory
        for disk_store_file_name in ["files_default", "files_static", "files_dynamic_ebs", "files_dynamic_s3"]:
            disk_store_path = os.path.join(temp_directory, disk_store_file_name)
            os.makedirs(disk_store_path)
            setattr(cls, "%s_path" % disk_store_file_name, disk_store_path)
        config_path = os.path.join(temp_directory, "object_store_conf.xml")
        with open(config_path, "w") as f:
            f.write(DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE.safe_substitute({"temp_directory": temp_directory}))
        config["object_store_config_file"] = config_path
        config["job_config_file"] = JOB_CONFIG_FILE
        config["job_resource_params_file"] = JOB_RESOURCE_PARAMETERS_CONFIG_FILE

    def setUp(self):
        super(ObjectStoreJobsIntegrationTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def _object_store_counts(self):
        files_default_count = _files_count(self.files_default_path)
        files_static_count = _files_count(self.files_static_path)
        files_dynamic_count = _files_count(self.files_dynamic_path)
        return files_default_count, files_static_count, files_dynamic_count

    def _assert_file_counts(self, default, static, dynamic_ebs, dynamic_s3):
        files_default_count = _files_count(self.files_default_path)
        files_static_count = _files_count(self.files_static_path)
        files_dynamic_ebs_count = _files_count(self.files_dynamic_ebs_path)
        files_dynamic_s3_count = _files_count(self.files_dynamic_s3_path)
        assert default == files_default_count
        assert static == files_static_count
        assert dynamic_ebs == files_dynamic_ebs_count
        assert dynamic_s3 == files_dynamic_s3_count

    def test_tool_simple_constructs(self):

        with self.dataset_populator.test_history() as history_id:

            def _run_tool(tool_id, inputs):
                self.dataset_populator.run_tool(
                    tool_id,
                    inputs,
                    history_id,
                    assert_ok=True,
                )
                self.dataset_populator.wait_for_history(history_id)

            self._assert_file_counts(0, 0, 0, 0)

            hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
            self.dataset_populator.wait_for_history(history_id)
            hda1_input = {"src": "hda", "id": hda1["id"]}

            # One file uploaded, added to default object store ID.
            self._assert_file_counts(1, 0, 0, 0)

            # should create two files in static object store.
            _run_tool("multi_data_param", {"f1": hda1_input, "f2": hda1_input})
            self._assert_file_counts(1, 2, 0, 0)

            # should create two files in ebs object store.
            create_10_inputs = {
                "input1": hda1_input,
                "input2": hda1_input,
            }
            _run_tool("create_10", create_10_inputs)
            self._assert_file_counts(1, 2, 10, 0)

            # should create 10 files in S3 object store.
            create_10_inputs = {
                "__job_resource|__job_resource__select": "yes",
                "__job_resource|how_store": "slow",
                "input1": hda1_input,
                "input2": hda1_input,
            }
            _run_tool("create_10", create_10_inputs)
            self._assert_file_counts(1, 2, 10, 10)


def _files_count(directory):
    return sum(len(files) for _, _, files in os.walk(directory))
