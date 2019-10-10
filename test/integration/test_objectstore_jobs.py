"""Integration tests for object stores."""

import os
import string

from base import integration_util  # noqa: I202
from base.populators import (
    DatasetPopulator,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_job_conf.xml")


DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE = string.Template("""<?xml version="1.0"?>
<object_store type="hierarchical">
    <backends>
        <object_store type="distributed" id="primary" order="0">
            <backends>
                <backend id="files1" type="disk" weight="1">
                    <files_dir path="${temp_directory}/files1"/>
                    <extra_dir type="temp" path="${temp_directory}/tmp1"/>
                    <extra_dir type="job_work" path="${temp_directory}/job_working_directory1"/>
                </backend>
                <backend id="files2" type="disk" weight="1">
                    <files_dir path="${temp_directory}/files2"/>
                    <extra_dir type="temp" path="${temp_directory}/tmp2"/>
                    <extra_dir type="job_work" path="${temp_directory}/job_working_directory2"/>
                </backend>
            </backends>
        </object_store>
        <object_store type="disk" id="secondary" order="1">
            <files_dir path="${temp_directory}/files3"/>
            <extra_dir type="temp" path="${temp_directory}/tmp3"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory3"/>
        </object_store>
    </backends>
</object_store>
""")


class ObjectStoreJobsIntegrationTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        temp_directory = cls._test_driver.mkdtemp()
        cls.object_stores_parent = temp_directory
        for disk_store_file_name in ["files1", "files2", "files3"]:
            disk_store_path = os.path.join(temp_directory, disk_store_file_name)
            os.makedirs(disk_store_path)
            setattr(cls, "%s_path" % disk_store_file_name, disk_store_path)
        config_path = os.path.join(temp_directory, "object_store_conf.xml")
        with open(config_path, "w") as f:
            f.write(DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE.safe_substitute({"temp_directory": temp_directory}))
        config["object_store_config_file"] = config_path

    def setUp(self):
        super(ObjectStoreJobsIntegrationTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_tool_simple_constructs(self):
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
            create_10_inputs = {
                "input1": {"src": "hda", "id": hda1["id"]},
                "input2": {"src": "hda", "id": hda1["id"]},
            }
            self.dataset_populator.run_tool(
                "create_10",
                create_10_inputs,
                history_id,
                assert_ok=True,
            )
            self.dataset_populator.wait_for_history(history_id)

        files_1_count = _files_count(self.files1_path)
        files_2_count = _files_count(self.files2_path)
        files_3_count = _files_count(self.files3_path)

        # Ensure no files written to the secondary/inactive hierarchical disk store.
        assert files_3_count == 0

        # Ensure the 10 inputs were written to one of the distributed object store's disk
        # stores (it will have either 10 or 11 depeending on whether the input was also
        # written there. The other disk store may or may not have the input file so should
        # have at most one file.
        assert (files_1_count >= 10) or (files_2_count >= 10)
        assert (files_1_count <= 1) or (files_2_count <= 1)

        # Other sanity checks on the test - just make sure the test was setup as intended
        # and not actually testing object store behavior.
        assert (files_1_count <= 11) and (files_2_count <= 11)
        assert (files_1_count >= 0) and (files_2_count >= 0)


def _files_count(directory):
    return sum(len(files) for _, _, files in os.walk(directory))
