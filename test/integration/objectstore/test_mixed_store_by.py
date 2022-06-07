"""Integration tests for mixing store_by."""

import os
import re
import string

from galaxy.util import is_uuid
from ._base import (
    BaseObjectStoreIntegrationTestCase,
    files_count,
)

DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE = string.Template(
    """<?xml version="1.0"?>
<object_store type="distributed" id="primary" order="0">
    <backends>
        <backend id="files1" type="disk" weight="1" store_by="uuid">
            <files_dir path="${temp_directory}/files1"/>
            <extra_dir type="temp" path="${temp_directory}/tmp1"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory1"/>
        </backend>
        <backend id="files2" type="disk" weight="1" store_by="id">
            <files_dir path="${temp_directory}/files2"/>
            <extra_dir type="temp" path="${temp_directory}/tmp2"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory2"/>
        </backend>
    </backends>
</object_store>
"""
)

TEST_INPUT_FILES_CONTENT = "1 2 3"


class MixedStoreByObjectStoreIntegrationTestCase(BaseObjectStoreIntegrationTestCase):
    # setup by _configure_object_store
    files1_path: str
    files2_path: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_object_store(DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE, config)

    def test_both_types(self):
        """Test each object store configures files correctly."""
        i = 0
        with self.dataset_populator.test_history() as history_id:
            # Loop breaks once each object store has at least once file of each type.
            while True:
                hda = self.dataset_populator.new_dataset(history_id, content=TEST_INPUT_FILES_CONTENT, wait=True)
                content = self.dataset_populator.get_history_dataset_content(history_id, hda["id"])
                assert content.strip() == TEST_INPUT_FILES_CONTENT
                files1_count = files_count(self.files1_path)
                files2_count = files_count(self.files2_path)
                if files1_count and files2_count:
                    break
                i += 1
                if i > 50:
                    raise Exception(
                        "Problem with logic of test, randomly each object store should have at least one file by now"
                    )

            def strip_to_id(x):
                match = re.match(r"dataset_(.*)\.dat", os.path.basename(x))
                assert match
                return match.group(1)

            files1_paths = [strip_to_id(p) for p in _get_datasets_files_in_path(self.files1_path)]
            files2_paths = [strip_to_id(p) for p in _get_datasets_files_in_path(self.files2_path)]
            for files1_path in files1_paths:
                assert is_uuid(files1_path)
            for files2_path in files2_paths:
                assert files2_path.isdigit()


def _get_datasets_files_in_path(directory):
    files = []
    for path, _, filename in os.walk(directory):
        for f in filename:
            if f.endswith(".dat"):
                files.append(os.path.join(path, f))
    return files
