from .framework import (
    SeleniumTestCase,
    selenium_test,
    UsesHistoryItemAssertions,
)


class UploadsTestCase(SeleniumTestCase, UsesHistoryItemAssertions):

    @selenium_test
    def test_upload_simplest(self):
        self.perform_upload(self.get_filename("1.sam"))

        self.history_panel_wait_for_hid_ok(1)
        history_contents = self.current_history_contents()
        history_count = len(history_contents)
        assert history_count == 1, "Incorrect number of items in history - expected 1, found %d" % history_count

        hda = history_contents[0]
        assert hda["name"] == '1.sam'
        assert hda["extension"] == "sam"

        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_dbkey_displayed_as(1, "?")

    @selenium_test
    def test_upload_specify_ext(self):
        self.perform_upload(self.get_filename("1.sam"), ext="txt")
        self.history_panel_wait_for_hid_ok(1)
        history_contents = self.current_history_contents()
        hda = history_contents[0]
        assert hda["name"] == '1.sam'
        assert hda["extension"] == "txt", hda

    @selenium_test
    def test_upload_specify_genome(self):
        self.perform_upload(self.get_filename("1.sam"), genome="hg18")
        self.history_panel_wait_for_hid_ok(1)

        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_dbkey_displayed_as(1, "hg18")

    @selenium_test
    def test_upload_specify_ext_all(self):
        self.perform_upload(self.get_filename("1.sam"), ext_all="txt")
        self.history_panel_wait_for_hid_ok(1)
        history_contents = self.current_history_contents()
        hda = history_contents[0]
        assert hda["name"] == '1.sam'
        assert hda["extension"] == "txt", hda

    @selenium_test
    def test_upload_specify_genome_all(self):
        self.perform_upload(self.get_filename("1.sam"), genome_all="hg18")
        self.history_panel_wait_for_hid_ok(1)

        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_dbkey_displayed_as(1, "hg18")

    @selenium_test
    def test_upload_list(self):
        self.upload_list([self.get_filename("1.tabular")], name="Test List")
        self.history_panel_wait_for_hid_ok(2)
        # Make sure modals disappeared - both List creator (TODO: upload).
        self.wait_for_selector_absent_or_hidden(".collection-creator")

        self.assert_item_name(2, "Test List")

        # Make sure source item is hidden when the collection is created.
        self.history_panel_wait_for_hid_hidden(1)

    @selenium_test
    def test_upload_pair(self):
        self.upload_list([self.get_filename("1.tabular"), self.get_filename("2.tabular")], name="Test Pair")
        self.history_panel_wait_for_hid_ok(3)
        # Make sure modals disappeared - both collection creator (TODO: upload).
        self.wait_for_selector_absent_or_hidden(".collection-creator")

        self.assert_item_name(3, "Test Pair")

        # Make sure source items are hidden when the collection is created.
        self.history_panel_wait_for_hid_hidden(1)
        self.history_panel_wait_for_hid_hidden(2)

    @selenium_test
    def test_upload_pair_specify_extension(self):
        self.upload_list([self.get_filename("1.tabular"), self.get_filename("2.tabular")], name="Test Pair", ext="txt", hide_source_items=False)
        self.history_panel_wait_for_hid_ok(3)
        self.history_panel_wait_for_hid_ok(1)

        history_contents = self.current_history_contents()
        hda = history_contents[0]
        assert hda["name"] == '1.tabular'
        assert hda["extension"] == "txt", hda

    @selenium_test
    def test_upload_paired_list(self):
        self.upload_paired_list([self.get_filename("1.tabular"), self.get_filename("2.tabular")], name="Test Paired List")
        self.history_panel_wait_for_hid_ok(3)
        # Make sure modals disappeared - both collection creator (TODO: upload).
        self.wait_for_selector_absent_or_hidden(".collection-creator")
        self.assert_item_name(3, "Test Paired List")

        # Make sure source items are hidden when the collection is created.
        self.history_panel_wait_for_hid_hidden(1)
        self.history_panel_wait_for_hid_hidden(2)
