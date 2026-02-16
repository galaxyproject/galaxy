"""Tests for the beta upload panel's direct collection creation flow.

These tests verify that the beta upload UI creates dataset collections
directly via HdcaDataItemsTarget (destination: hdca) in a single
/api/tools/fetch request, rather than using the older two-step approach
of uploading individual datasets then creating a collection separately.
"""

from .framework import (
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)


class TestBetaUploadCollection(SeleniumTestCase, UsesHistoryItemAssertions):
    """Tests for direct collection creation through the beta upload panel."""

    ensure_registered = True

    def _navigate_to_beta_upload_method(self, method_id):
        """Navigate to a specific beta upload method via the activity bar.

        Opens the activity settings panel, clicks the Beta Upload activity
        to open its sidebar panel, then clicks the desired upload method
        which navigates to the upload method view via router.push().
        """
        self.home()
        # Open activity settings panel
        self.components.preferences.activity.wait_for_and_click()
        # Click the Beta Upload activity in settings to open its sidebar panel
        self.components.beta_upload.activity.wait_for_and_click()
        # Wait for and click the specific upload method card in the sidebar
        self.components.beta_upload.method_card(method_id=method_id).wait_for_and_click()

    def _paste_urls_and_add(self, urls):
        """Paste URLs into the paste-links textarea and click Add URLs."""
        textarea = self.components.beta_upload.paste_textarea.wait_for_visible()
        textarea.send_keys("\n".join(urls))
        # Click the Add URLs button
        self.components.beta_upload.add_urls_button.wait_for_and_click()

    def _enable_collection_creation(self, name, collection_type="list"):
        """Enable collection creation toggle and set name/type."""
        # Click the "Create a collection" toggle checkbox
        self.components.beta_upload.collection_section.wait_for_and_click()

        # Wait for the collection config form to appear
        name_input = self.components.beta_upload.collection_name_input.wait_for_visible()
        name_input.clear()
        name_input.send_keys(name)

        # Set collection type if not default
        if collection_type != "list":
            self.components.beta_upload.collection_type_select.wait_for_visible()
            self.components.beta_upload.collection_type_select.select_by_value(collection_type)

    def _click_start_upload(self):
        """Click the Start button in the upload footer."""
        self.components.beta_upload.start_button.wait_for_and_click()

    @selenium_test
    def test_beta_upload_paste_links_as_list_collection(self):
        """Test creating a list collection directly from pasted URLs."""
        self._navigate_to_beta_upload_method("paste-links")

        # Paste two URLs
        test_urls = [
            "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed",
            "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/2.bed",
        ]
        self._paste_urls_and_add(test_urls)

        # Enable collection creation
        self._enable_collection_creation("Test List Collection")

        # Start the upload
        self._click_start_upload()

        # The direct HDCA creation should create a collection directly in history.
        # With direct collection creation (destination: hdca), only the collection
        # appears in history - no individual datasets are created.
        # The collection will be at HID 1 since it's created directly.
        self.history_panel_wait_for_hid_ok(1)

        # Verify the collection name
        self.assert_item_name(1, "Test List Collection")

    @selenium_test
    def test_beta_upload_paste_links_as_paired_collection(self):
        """Test creating a list:paired collection directly from pasted URLs."""
        self._navigate_to_beta_upload_method("paste-links")

        # Paste two URLs (will be paired as forward/reverse)
        test_urls = [
            "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed",
            "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/2.bed",
        ]
        self._paste_urls_and_add(test_urls)

        # Enable collection creation as list:paired
        self._enable_collection_creation("Test Paired Collection", collection_type="list:paired")

        # Start the upload
        self._click_start_upload()

        # Collection should appear directly
        self.history_panel_wait_for_hid_ok(1)
        self.assert_item_name(1, "Test Paired Collection")
