"""Integration tests for job and object store interactions."""

import os
import string

from ._base import (
    BaseObjectStoreIntegrationTestCase,
    files_count,
)

DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE = string.Template(
    """<?xml version="1.0"?>
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
"""
)

TEST_INPUT_FILES_CONTENT = "1 2 3"


class ObjectStoreJobsIntegrationTestCase(BaseObjectStoreIntegrationTestCase):
    # setup by _configure_object_store
    files1_path: str
    files2_path: str
    files3_path: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_object_store(DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE, config)

    def setUp(self):
        super().setUp()
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content=TEST_INPUT_FILES_CONTENT)
            create_10_inputs = {
                "input1": {"src": "hda", "id": hda1["id"]},
                "input2": {"src": "hda", "id": hda1["id"]},
            }
            self.dataset_populator.run_tool(
                "create_10",
                create_10_inputs,
                history_id,
            )
            self.dataset_populator.wait_for_history(history_id)

    def test_files_count_and_content_in_each_objectstore_backend(self):
        """
        According to the ObjectStore configuration given in the
        `DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE` variable, datasets
        can be stored on three backends, named:
            -   primary/files1;
            -   primary/files2;
            -   secondary/files3.

        Objectstore _randomly_ distributes tools outputs on
        `primary/files1` and `primary/files2`, and will use
        `secondary/files3` if both `primary` backends fail.

        This test runs a tools that creates ten dummy datasets,
        and asserts if ObjectStore correctly creates ten files
        in `primary/files1` and `primary/files2`, and none in
        `secondary/files3`, assuming it will not fail persisting
        data in `primary` backend.
        """
        files_1_count = files_count(self.files1_path)
        files_2_count = files_count(self.files2_path)
        files_3_count = files_count(self.files3_path)

        # Ensure no files written to the secondary/inactive hierarchical disk store.
        assert files_3_count == 0

        # Ensure the 10 inputs were written to one of the distributed object store's disk
        # stores (it will have either 10 or 11 depending on whether the input was also
        # written there. The other disk store may or may not have the input file so should
        # have at most one file.
        assert (files_1_count + files_2_count == 10) or (files_1_count + files_2_count == 11)

        # Other sanity checks on the test - just make sure the test was setup as intended
        # and not actually testing object store behavior.
        assert (files_1_count <= 11) and (files_2_count <= 11)
        assert (files_1_count >= 0) and (files_2_count >= 0)

        # TODO: ideally the following assertion should be separated in a different test method.
        contents = []
        path1_files = _get_datasets_files_in_path(self.files1_path)
        path2_files = _get_datasets_files_in_path(self.files2_path)
        path3_files = _get_datasets_files_in_path(self.files3_path)
        for filename in path1_files + path2_files + path3_files:
            with open(filename) as f:
                content = f.read().strip()
                if content != TEST_INPUT_FILES_CONTENT:
                    contents.append(content)

        for expected_content in range(1, 10):
            assert str(expected_content) in contents


def _get_datasets_files_in_path(directory):
    files = []
    for path, _, filename in os.walk(directory):
        for f in filename:
            if f.endswith(".dat"):
                files.append(os.path.join(path, f))
    return files
