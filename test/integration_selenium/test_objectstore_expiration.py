import string
from typing import (
    Literal,
    TYPE_CHECKING,
)

from galaxy_test.driver.integration_util import ConfiguresObjectStores
from galaxy_test.selenium.framework import managed_history
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)

if TYPE_CHECKING:
    from galaxy_test.selenium.framework import (
        SeleniumSessionDatasetCollectionPopulator,
        SeleniumSessionDatasetPopulator,
    )

OBJECT_STORES_CONFIG = string.Template(
    """
type: distributed
backends:
  - id: default
    type: disk
    weight: 1
    allow_selection: true
    name: ${default_name}
    files_dir: "${temp_directory}/files0"
    extra_dirs:
    - type: temp
      path: "${temp_directory}/tmp0"
    - type: job_work
      path: "${temp_directory}/job_working_directory0"

  - id: short_term
    type: disk
    weight: 1
    allow_selection: true
    name: ${short_term_name}
    files_dir: "${temp_directory}/files1"
    extra_dirs:
    - type: temp
      path: "${temp_directory}/tmp1"
    - type: job_work
      path: "${temp_directory}/job_working_directory1"
    object_expires_after_days: ${short_term_expiration_days}

  - id: mid_term
    type: disk
    weight: 1
    allow_selection: true
    name: ${mid_term_name}
    files_dir: "${temp_directory}/files2"
    extra_dirs:
    - type: temp
      path: "${temp_directory}/tmp2"
    - type: job_work
      path: "${temp_directory}/job_working_directory2"
    object_expires_after_days: ${mid_term_expiration_days}
"""
)

AvailableObjectStoreIDs = Literal["default", "short_term", "mid_term"]


class TestObjectStoreContentsExpirationIntegration(SeleniumIntegrationTestCase, ConfiguresObjectStores):
    ensure_registered = True
    dataset_populator: "SeleniumSessionDatasetPopulator"
    dataset_collection_populator: "SeleniumSessionDatasetCollectionPopulator"

    template_params = {
        "default_name": "Default Storage",
        "short_term_name": "Test Short Term Storage",
        "mid_term_name": "Test Mid Term Storage",
        "short_term_expiration_days": 5,
        "mid_term_expiration_days": 30,
    }

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        super()._configure_object_store(
            OBJECT_STORES_CONFIG,
            config,
            template_params=cls.template_params,
            format="yml",
        )
        config["object_store_store_by"] = "uuid"
        config["outputs_to_working_directory"] = True

    @selenium_test
    @managed_history
    def test_no_expiration_for_default_storage(self):
        self._select_history_storage("default")

        self.perform_upload_of_pasted_content("default storage content")
        self.history_panel_wait_for_hid_visible(1)
        self._assert_no_expiration_indicator_for(hid=1)

    @selenium_test
    @managed_history
    def test_expiration_of_single_dataset(self):
        self._select_history_storage("short_term")

        self.perform_upload_of_pasted_content("my test content")
        self.history_panel_wait_for_hid_visible(1)
        self._assert_expiration_indicator_visible_for(hid=1, expected_storage_id="short_term")

    @selenium_test
    @managed_history
    def test_expiration_of_collection(self):
        self._select_history_storage("short_term")

        self.perform_upload_of_pasted_content("dataset 1 content")
        self.history_panel_wait_for_hid_visible(1)

        self.perform_upload_of_pasted_content("dataset 2 content")
        self.history_panel_wait_for_hid_visible(2)

        self.history_panel_wait_for_and_select([1, 2])
        self.history_panel_build_list_auto()
        self.collection_builder_set_name("Test Collection")
        self.collection_builder_create()
        self.history_panel_wait_for_hid_visible(5)

        self._assert_expiration_indicator_visible_for(hid=5, expected_storage_id="short_term")

    @selenium_test
    @managed_history
    def test_expiration_if_mixed_storage_in_collection(self):
        self._select_history_storage("default")

        self.perform_upload_of_pasted_content("dataset stored in default storage")
        self.history_panel_wait_for_hid_visible(1)
        self._assert_no_expiration_indicator_for(hid=1)

        self._select_history_storage("short_term")

        self.perform_upload_of_pasted_content("dataset stored in short term storage")
        self.history_panel_wait_for_hid_visible(2)
        self._assert_expiration_indicator_visible_for(hid=2, expected_storage_id="short_term")

        self._select_history_storage("mid_term")

        self.perform_upload_of_pasted_content("dataset stored in mid term storage")
        self.history_panel_wait_for_hid_visible(3)
        self._assert_expiration_indicator_visible_for(hid=3, expected_storage_id="mid_term")

        self.history_panel_wait_for_and_select([1, 2, 3])
        self.history_panel_build_list_auto()
        self.collection_builder_set_name("Test Collection")
        self.collection_builder_create()
        self.history_panel_wait_for_hid_visible(7)

        # The collection should show the shortest expiration time of its contents
        self._assert_expiration_indicator_visible_for(hid=7, expected_storage_id="short_term")

    def _get_expiration_indicator_for(self, hid: int):
        content_item = self.content_item_by_attributes(hid=hid)
        expiration_indicator = content_item.expiration_indicator_badge
        return expiration_indicator

    def _assert_no_expiration_indicator_for(self, hid: int):
        expiration_indicator = self._get_expiration_indicator_for(hid)
        assert expiration_indicator.is_absent

    def _assert_expiration_indicator_visible_for(self, hid: int, expected_storage_id: AvailableObjectStoreIDs):
        expiration_indicator = self._get_expiration_indicator_for(hid).wait_for_visible()
        # The indicator should mention the remaining days to expiration
        text = expiration_indicator.text
        remaining_days = int(str(self.template_params.get(f"{expected_storage_id}_expiration_days", 0))) - 1
        assert all(keyword in text.lower() for keyword in ["expire", str(remaining_days)])

        # The tooltip should mention the storage name
        tooltip_text = expiration_indicator.get_attribute("title")
        assert tooltip_text is not None
        expected_storage_name = str(self.template_params.get(f"{expected_storage_id}_name", ""))
        assert all(keyword in tooltip_text.lower() for keyword in ["expires", expected_storage_name.lower()])

    def _select_history_storage(self, storage_id: AvailableObjectStoreIDs):
        self.select_history_storage(storage_id)
