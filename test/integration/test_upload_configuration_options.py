"""Integration tests various upload aspects.

This file checks upload options that require different non-default Galaxy
configuration options. More vanilla upload options and behaviors are tested
with the API test framework (located in test_tools.py).

These options include:
 - The config optiond check_upload_content and allow_path_paste.
 - The upload API parameter auto_decompress.
 - Checking for malicious content in uploads of compressed files.
 - Restricting file:// uploads to admins and allowing them only when
   allow_path_paste is set to True.
"""

import os

from base import integration_util
from base.populators import DatasetPopulator

SCRIPT_DIR = os.path.normpath(os.path.dirname(__file__))
TEST_DATA_DIRECTORY = os.path.join(SCRIPT_DIR, os.pardir, os.pardir, "test-data")


class BaseCheckUploadContentConfigurationTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True

    def setUp(self):
        super(BaseCheckUploadContentConfigurationTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.history_id = self.dataset_populator.new_history()


class NonAdminsCannotPasteFilePathTestCase(BaseCheckUploadContentConfigurationTestCase):

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["allow_path_paste"] = True

    def test(self):
        payload = self.dataset_populator.upload_payload(
            self.history_id, 'file://%s/1.RData' % TEST_DATA_DIRECTORY, ext="binary"
        )
        create_response = self._post("tools", data=payload)
        # Ideally this would be 403 but the tool API endpoint isn't using
        # the newer API decorator that handles those details.
        assert create_response.status_code >= 400


class AdminsCanPasteFilePathsTestCase(BaseCheckUploadContentConfigurationTestCase):

    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["allow_path_paste"] = True

    def test(self):
        payload = self.dataset_populator.upload_payload(
            self.history_id, 'file://%s/random-file' % TEST_DATA_DIRECTORY,
        )
        create_response = self._post("tools", data=payload)
        # Ideally this would be 403 but the tool API endpoint isn't using
        # the newer API decorator that handles those details.
        assert create_response.status_code == 200


class DefaultBinaryContentFiltersTestCase(BaseCheckUploadContentConfigurationTestCase):

    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["allow_path_paste"] = True

    def test_random_binary_allowed(self):
        dataset = self.dataset_populator.new_dataset(
            self.history_id, 'file://%s/random-file' % TEST_DATA_DIRECTORY, file_type="auto", wait=True
        )
        dataset = self.dataset_populator.get_history_dataset_details(self.history_id, dataset=dataset)
        assert dataset["file_ext"] == "data", dataset

    def test_gzipped_html_content_blocked_by_default(self):
        dataset = self.dataset_populator.new_dataset(
            self.history_id, 'file://%s/bad.html.gz' % TEST_DATA_DIRECTORY, file_type="auto", wait=True
        )
        dataset = self.dataset_populator.get_history_dataset_details(self.history_id, dataset=dataset)
        assert dataset["file_size"] == 0


class DisableContentCheckingTestCase(BaseCheckUploadContentConfigurationTestCase):

    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["allow_path_paste"] = True
        config["check_upload_content"] = False

    def test_gzipped_html_content_now_allowed(self):
        dataset = self.dataset_populator.new_dataset(
            self.history_id, 'file://%s/bad.html.gz' % TEST_DATA_DIRECTORY, file_type="auto", wait=True
        )
        dataset = self.dataset_populator.get_history_dataset_details(self.history_id, dataset=dataset)
        # Same file was empty above!
        assert dataset["file_size"] != 0


class AutoDecompressTestCase(BaseCheckUploadContentConfigurationTestCase):

    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["allow_path_paste"] = True

    def test_auto_decompress_off(self):
        dataset = self.dataset_populator.new_dataset(
            self.history_id, 'file://%s/1.sam.gz' % TEST_DATA_DIRECTORY, file_type="auto", auto_decompress=False, wait=True
        )
        dataset = self.dataset_populator.get_history_dataset_details(self.history_id, dataset=dataset)
        assert dataset["file_ext"] == "data", dataset

    def test_auto_decompress_on(self):
        dataset = self.dataset_populator.new_dataset(
            self.history_id, 'file://%s/1.sam.gz' % TEST_DATA_DIRECTORY, file_type="auto", wait=True
        )
        dataset = self.dataset_populator.get_history_dataset_details(self.history_id, dataset=dataset)
        assert dataset["file_ext"] == "sam", dataset


class LocalAddressWhitelisting(BaseCheckUploadContentConfigurationTestCase):

    def test_external_url(self):
        payload = self.dataset_populator.upload_payload(
            self.history_id, 'http://localhost/', ext="txt"
        )
        create_response = self._post("tools", data=payload)
        # Ideally this would be 403 but the tool API endpoint isn't using
        # the newer API decorator that handles those details.
        assert create_response.status_code >= 400
