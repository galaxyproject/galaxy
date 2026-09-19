from typing import TYPE_CHECKING

from galaxy_test.driver.integration_util import ConfiguresObjectStores
from galaxy_test.selenium.upload_activity_helpers import UsesUploadActivity
from .framework import (
    managed_history,
    selenium_test,
    SeleniumIntegrationTestCase,
)
from .test_objectstore_selection import MSI_EXAMPLE_OBJECT_STORE_CONFIG_TEMPLATE

if TYPE_CHECKING:
    from galaxy_test.selenium.framework import SeleniumSessionDatasetPopulator


class TestUploadTargetObjectStoreSelectionSeleniumIntegration(
    SeleniumIntegrationTestCase,
    ConfiguresObjectStores,
    UsesUploadActivity,
):
    ensure_registered = True
    dataset_populator: "SeleniumSessionDatasetPopulator"

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._configure_object_store(MSI_EXAMPLE_OBJECT_STORE_CONFIG_TEMPLATE, config)

    @selenium_test
    @managed_history
    def test_uploads_can_target_different_object_stores(self):
        """Test that users can select different object stores for uploads using the TargetObjectStoreSelector.

        This test verifies the new upload advanced mode feature that allows selecting a target
        object store during upload, rather than relying on history preferences. It exercises
        both directions: an explicit store selection and the default (history preference) path,
        then verifies each dataset landed in the correct store.
        """
        selectable_object_store_ids = self.dataset_populator.selectable_object_store_ids()
        assert "second" in selectable_object_store_ids, selectable_object_store_ids
        custom_store_id = "second"
        default_store_id = "high_performance"
        first_file_path = self.test_data_resolver.get_filename("1.txt")
        second_file_path = self.test_data_resolver.get_filename("2.txt")

        # Upload first file with explicit (non-default) store selection
        local_upload = self.upload_context("local-file")

        # Switch on advanced mode to reveal the TargetObjectStoreSelector and make an explicit store selection
        local_upload.set_advanced_mode(True)

        local_upload.select_target_object_store(custom_store_id)
        local_upload.stage_local_file(first_file_path, {"name": "custom-store-dataset"}).start()
        self.history_panel_wait_for_hid_ok(1)

        # Upload second file with default store (no explicit selection)
        self.upload_context("local-file").stage_local_file(second_file_path, {"name": "default-store-dataset"}).start()
        self.history_panel_wait_for_hid_ok(2)

        # Verify both datasets are in the history
        history_id = self.current_history_id()
        history_contents = self.dataset_populator.get_history_contents(history_id)
        datasets_by_name = {
            content["name"]: content
            for content in history_contents
            if content.get("history_content_type") == "dataset"
            and content.get("name") in ["custom-store-dataset", "default-store-dataset"]
        }
        assert "custom-store-dataset" in datasets_by_name, history_contents
        assert "default-store-dataset" in datasets_by_name, history_contents

        # Verify each dataset landed in the expected store
        custom_storage = self.dataset_populator.dataset_storage_info(datasets_by_name["custom-store-dataset"]["id"])
        default_storage = self.dataset_populator.dataset_storage_info(datasets_by_name["default-store-dataset"]["id"])
        assert custom_storage["object_store_id"] == custom_store_id, custom_storage
        assert default_storage["object_store_id"] == default_store_id, default_storage
