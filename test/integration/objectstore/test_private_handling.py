"""Integration tests for private object store handling."""

import string

from galaxy_test.base import api_asserts
from ._base import BaseObjectStoreIntegrationTestCase

PRIVATE_OBJECT_STORE_CONFIG_TEMPLATE = string.Template(
    """<?xml version="1.0"?>
<object_store type="disk" id="primary" private="true">
    <files_dir path="${temp_directory}/files1"/>
    <extra_dir type="temp" path="${temp_directory}/tmp1"/>
    <extra_dir type="job_work" path="${temp_directory}/job_working_directory1"/>
</object_store>
"""
)

TEST_INPUT_FILES_CONTENT = "1 2 3"


class TestPrivatePreventsSharingObjectStoreIntegration(BaseObjectStoreIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["new_user_dataset_access_role_default_private"] = True
        cls._configure_object_store(PRIVATE_OBJECT_STORE_CONFIG_TEMPLATE, config)

    def test_both_types(self):
        """Test each object store configures files correctly."""
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content=TEST_INPUT_FILES_CONTENT, wait=True)
            content = self.dataset_populator.get_history_dataset_content(history_id, hda["id"])
            assert content.startswith(TEST_INPUT_FILES_CONTENT)
            response = self.dataset_populator.make_dataset_public_raw(history_id, hda["id"])
            api_asserts.assert_status_code_is(response, 400)
            api_asserts.assert_error_code_is(response, 400008)
            api_asserts.assert_error_message_contains(response, "Attempting to share a non-shareable dataset.")


class TestPrivateCannotWritePublicDataObjectStoreIntegration(BaseObjectStoreIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["new_user_dataset_access_role_default_private"] = False
        cls._configure_object_store(PRIVATE_OBJECT_STORE_CONFIG_TEMPLATE, config)

    def test_both_types(self):
        with self.dataset_populator.test_history() as history_id:
            response = self.dataset_populator.new_dataset_request(
                history_id, content=TEST_INPUT_FILES_CONTENT, wait=True, assert_ok=False
            )
            job = response.json()["jobs"][0]
            final_state = self.dataset_populator.wait_for_job(job["id"])
            assert final_state == "error"
