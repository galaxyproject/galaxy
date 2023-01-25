"""Integration tests for structured datasets (currently only HDF5 supported).

This file checks the ability to access datasets using the get_structured_content
API and services.
"""

import os

from galaxy_test.base.populators import (
    DatasetPopulator,
)
from galaxy_test.driver import integration_util

SCRIPT_DIR = os.path.normpath(os.path.dirname(__file__))
TEST_DATA_DIRECTORY = os.path.join(SCRIPT_DIR, os.pardir, os.pardir, "test-data")


class StructuredDatasetTestCase(integration_util.IntegrationTestCase):
    require_admin_user = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.history_id = self.dataset_populator.new_history()

    def test_fail_on_nonbinary(self):
        dataset_id = self.dataset_populator.new_dataset(
            self.history_id, "file://%s/random-file" % TEST_DATA_DIRECTORY, file_type="txt", wait=True
        )["dataset_id"]
        response = self._get(f"datasets/{dataset_id}/content/meta")
        self._assert_status_code_is(response, 500)

    def test_meta(self):
        dataset_id = self.dataset_populator.new_dataset(
            self.history_id, "file://%s/chopper.h5" % TEST_DATA_DIRECTORY, file_type="h5", wait=True
        )["dataset_id"]
        # check meta API
        response = self._get(f"datasets/{dataset_id}/content/meta")
        self._assert_status_code_is(response, 200)
        hvals = response.json()
        self._assert_has_keys(hvals, "attributes", "name", "type")

    def test_attr(self):
        dataset_id = self.dataset_populator.new_dataset(
            self.history_id, "file://%s/chopper.h5" % TEST_DATA_DIRECTORY, file_type="h5", wait=True
        )["dataset_id"]
        # check attr API
        response = self._get(f"datasets/{dataset_id}/content/attr")
        self._assert_status_code_is(response, 200)
        hvals = response.json()
        self._assert_has_keys(hvals, "HDF5_Version", "NeXus_version", "default", "file_name", "file_time")        
    
    def test_stats(self):
        dataset_id = self.dataset_populator.new_dataset(
            self.history_id, "file://%s/chopper.h5" % TEST_DATA_DIRECTORY, file_type="h5", wait=True
        )["dataset_id"]
        # check stats API
        response = self._get(f"datasets/{dataset_id}/content/stats?path=%2Fentry%2Fdata%2Fdata")
        self._assert_status_code_is(response, 200)
        hvals = response.json()
        self._assert_has_keys(hvals, "strict_positive_min", "positive_min", "min", "max", "mean", "std")
    
    def test_data(self):
        dataset_id = self.dataset_populator.new_dataset(
            self.history_id, "file://%s/chopper.h5" % TEST_DATA_DIRECTORY, file_type="h5", wait=True
        )["dataset_id"]
        # check data API
        response = self._get(f"datasets/{dataset_id}/content/stats?path=%2Fentry%2Fdata%2Fdata")
        self._assert_status_code_is(response, 200)
        hvals = response.json()
        self._assert_has_keys(hvals, "strict_positive_min", "positive_min", "min", "max", "mean", "std")          
