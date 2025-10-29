import pytest
from selenium.webdriver.common.by import By

from galaxy.selenium.stories.data.upload import (
    RULES_EXAMPLE_6_SOURCE,
    UploadStoriesMixin,
)
from .framework import (
    selenium_only,
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)


class TestUploads(SeleniumTestCase, UsesHistoryItemAssertions, UploadStoriesMixin):
    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_upload_file(self):
        self.perform_upload(self.get_filename("1.sam"))

        self.history_panel_wait_for_hid_ok(1)
        history_count = len(self.history_contents())
        assert history_count == 1, f"Incorrect number of items in history - expected 1, found {history_count}"

        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_summary_includes(1, "28 lines")

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_upload_pasted_content(self):
        pasted_content = "this is pasted"
        self.perform_upload_of_pasted_content(pasted_content)

        self.history_panel_wait_for_hid_ok(1)
        history_count = len(self.history_contents())
        assert history_count == 1, f"Incorrect number of items in history - expected 1, found {history_count}"

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_upload_pasted_url_content(self):
        pasted_content = "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/LICENSE.txt"
        self.perform_upload_of_pasted_content(pasted_content)

        self.history_panel_wait_for_hid_ok(1)
        history_count = len(self.history_contents())
        assert history_count == 1, f"Incorrect number of items in history - expected 1, found {history_count}"

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_upload_composite_dataset_pasted_data(self):
        paste_content = ["a", "b", "c"]
        self.perform_upload_of_composite_dataset_pasted_data("velvet", paste_content)

        self.history_panel_wait_for_hid_ok(1)
        history_count = len(self.history_contents())
        assert history_count == 1, f"Incorrect number of items in history - expected 1, found {history_count}"

        self.history_panel_click_item_title(hid=1, wait=True)
        self.history_panel_item_view_dataset_details(1)
        param_values = self.driver.find_element(By.CSS_SELECTOR, "#tool-parameters td.tool-parameter-value .vjs-tree")
        request_json = param_values.get_attribute("data-request-json")
        assert request_json
        for data in paste_content:
            assert f'"paste_content":"{data}"' in request_json

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_upload_simplest(self):
        self.perform_upload(self.get_filename("1.sam"))

        self.history_panel_wait_for_hid_ok(1)
        history_contents = self.history_contents()
        history_count = len(history_contents)
        assert history_count == 1, f"Incorrect number of items in history - expected 1, found {history_count}"

        hda = history_contents[0]
        assert hda["name"] == "1.sam", hda
        assert hda["extension"] == "sam", hda

        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_dbkey_displayed_as(1, "?")

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_upload_specify_ext(self):
        self.perform_upload(self.get_filename("1.sam"), ext="txt")
        self.history_panel_wait_for_hid_ok(1)
        history_contents = self.history_contents()
        hda = history_contents[0]
        assert hda["name"] == "1.sam"
        assert hda["extension"] == "txt", hda

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_upload_specify_genome(self):
        self.perform_upload(self.get_filename("1.sam"), genome="hg18")
        self.history_panel_wait_for_hid_ok(1)

        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_dbkey_displayed_as(1, "hg18")

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_upload_specify_ext_all(self):
        self.perform_upload(self.get_filename("1.sam"), ext_all="txt")
        self.history_panel_wait_for_hid_ok(1)
        history_contents = self.history_contents()
        hda = history_contents[0]
        assert hda["name"] == "1.sam"
        assert hda["extension"] == "txt", hda

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_upload_specify_genome_all(self):
        self.perform_upload(self.get_filename("1.sam"), genome_all="hg18")
        self.history_panel_wait_for_hid_ok(1)

        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_dbkey_displayed_as(1, "hg18")

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_upload_deferred(self):
        self.perform_upload_of_pasted_content(
            "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed", deferred=True
        )
        hid = 1
        self.history_panel_wait_for_hid_deferred(hid)
        self.history_panel_click_item_title(hid=hid, wait=True)
        self.screenshot("history_panel_dataset_deferred")

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_upload_list(self):
        self.upload_list([self.get_filename("1.tabular")], name="Test List")
        self.history_panel_wait_for_hid_ok(3)
        # Make sure modals disappeared - both List creator (TODO: upload).
        self.wait_for_selector_absent_or_hidden(".collection-creator")

        self.assert_item_name(3, "Test List")

        # Make sure source item is hidden when the collection is created.
        self.history_panel_wait_for_hid_hidden(1)

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_upload_pair(self):
        self.upload_list([self.get_filename("1.tabular"), self.get_filename("2.tabular")], name="Test Pair")
        self.history_panel_wait_for_hid_ok(5)
        # Make sure modals disappeared - both collection creator (TODO: upload).
        self.wait_for_selector_absent_or_hidden(".collection-creator")

        self.assert_item_name(5, "Test Pair")

        # Make sure source items are hidden when the collection is created.
        self.history_panel_wait_for_hid_hidden(1)
        self.history_panel_wait_for_hid_hidden(2)
        self.history_panel_wait_for_hid_hidden(3)
        self.history_panel_wait_for_hid_hidden(4)

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_upload_pair_specify_extension(self):
        self.upload_list(
            [self.get_filename("1.tabular"), self.get_filename("2.tabular")],
            name="Test Pair",
            ext="txt",
            hide_source_items=False,
        )
        self.history_panel_wait_for_hid_ok(5)
        self.history_panel_wait_for_hid_ok(1)

        history_contents = self.history_contents()
        hda = history_contents[0]
        assert hda["name"] == "1.tabular"
        assert hda["extension"] == "txt", hda

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_upload_paired_list(self):
        self.upload_paired_list(
            [self.get_filename("1.tabular"), self.get_filename("2.tabular")], name="Test Paired List"
        )
        self.history_panel_wait_for_hid_ok(5)
        # Make sure modals disappeared - both collection creator (TODO: upload).
        self.wait_for_selector_absent_or_hidden(".collection-creator")
        self.assert_item_name(5, "Test Paired List")

        # Make sure source items are hidden when the collection is created.
        self.history_panel_wait_for_hid_hidden(1)
        self.history_panel_wait_for_hid_hidden(2)
        self.history_panel_wait_for_hid_hidden(3)
        self.history_panel_wait_for_hid_hidden(4)

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_upload_modal_retains_content(self):
        self.home()

        # initialize 2 uploads and close modal
        self.upload_start_click()
        self.upload_queue_local_file(self.get_filename("1.sam"))
        self.upload_paste_data("some pasted data")
        self.components.upload.close_button.wait_for_and_click()

        # reopen modal and check that the files are still there
        self.upload_start_click()
        self.wait_for_selector_visible("#upload-row-0.upload-init")
        self.wait_for_selector_visible("#upload-row-1.upload-init")

        # perform upload and close modal
        self.upload_start()
        self.components.upload.close_button.wait_for_and_click()

        # add another pasted file, but don't upload it
        self.upload_start_click()
        self.upload_paste_data("some more pasted data")
        self.components.upload.close_button.wait_for_and_click()

        # reopen modal and see 2 uploaded, 1 yet to upload
        self.upload_start_click()
        self.wait_for_selector_visible("#upload-row-0.upload-success")
        self.wait_for_selector_visible("#upload-row-1.upload-success")
        self.wait_for_selector_visible("#upload-row-2.upload-init")

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    @pytest.mark.gtn_screenshot
    @pytest.mark.local
    def test_rules_example_1_datasets(self):
        # Test case generated for:
        #   https://www.ebi.ac.uk/ena/data/view/PRJDA60709
        self.upload_rules_example_1()

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    @pytest.mark.gtn_screenshot
    @pytest.mark.local
    def test_rules_example_2_list(self):
        self.upload_rules_example_2()

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    @pytest.mark.gtn_screenshot
    @pytest.mark.local
    def test_rules_example_3_list_pairs(self):
        self.upload_rules_example_3()

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    @pytest.mark.gtn_screenshot
    @pytest.mark.local
    def test_rules_example_4_accessions(self):
        self.upload_rules_example_4()

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    @pytest.mark.gtn_screenshot
    @pytest.mark.local
    def test_rules_example_5_matching_collections(self):
        self.upload_rules_example_5()

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    @pytest.mark.gtn_screenshot
    @pytest.mark.local
    def test_rules_example_6_nested_lists(self):
        self.upload_rules_example_6()

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    @pytest.mark.local
    def test_rules_deferred_datasets(self):
        # Test case generated for:
        #   https://www.ebi.ac.uk/ena/data/view/PRJDA60709
        self.home()
        self.upload_rule_start()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("rules_deferred_datasets_1_rules_landing")
        self.components.upload.rule_source_content.wait_for_and_send_keys(
            """study_accession sample_accession    experiment_accession    fastq_ftp
PRJDA60709  SAMD00016379    DRX000475   ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000770/DRR000770.fastq.gz
PRJDA60709  SAMD00016383    DRX000476   ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000771/DRR000771.fastq.gz
PRJDA60709  SAMD00016380    DRX000477   ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000772/DRR000772.fastq.gz
PRJDA60709  SAMD00016378    DRX000478   ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000773/DRR000773.fastq.gz
PRJDA60709  SAMD00016381    DRX000479   ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000774/DRR000774.fastq.gz
PRJDA60709  SAMD00016382    DRX000480   ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000775/DRR000775.fastq.gz"""
        )
        self.wait_for_upload_modal()
        self.screenshot("rules_deferred_datasets_2_paste")
        self.upload_rule_build()
        rule_builder = self.components.rule_builder
        rule_builder._.wait_for_and_click()
        self.screenshot("rules_deferred_datasets_3_initial_rules")
        rule_builder.menu_button_filter.wait_for_and_click()
        self.screenshot("rule_builder_filters")
        rule_builder.menu_item_rule_type(rule_type="add-filter-count").wait_for_and_click()
        filter_editor = rule_builder.rule_editor(rule_type="add-filter-count")
        filter_editor_element = filter_editor.wait_for_visible()
        filter_input = filter_editor_element.find_element(By.CSS_SELECTOR, "input[type='number']")
        filter_input.clear()
        filter_input.send_keys("1")
        self.screenshot("rules_deferred_datasets_4_filter_header")
        rule_builder.rule_editor_ok.wait_for_and_click()
        self.rule_builder_set_mapping("url-deferred", "D")
        self.rule_builder_set_mapping("name", "C", screenshot_name="rules_deferred_datasets_5_mapping_edit")
        self.screenshot("rules_deferred_datasets_6_mapping_set")
        self.rule_builder_set_extension("fastqsanger.gz")
        self.screenshot("rules_deferred_datasets_7_extension_set")
        rule_builder.main_button_ok.wait_for_and_click()
        self.history_panel_wait_for_hid_deferred(6)
        self.screenshot("rules_deferred_datasets_8_download_complete")

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    @pytest.mark.local
    def test_rules_deferred_list(self):
        self.home()
        self.perform_upload(RULES_EXAMPLE_6_SOURCE)
        self.history_panel_wait_for_hid_ok(1)
        self.upload_rule_start()
        self.upload_rule_set_data_type("Collections")
        self.upload_rule_dataset_dialog()
        self.upload_rule_set_dataset(1)

        self.wait_for_upload_modal()
        self.screenshot("rules_deferred_list_1_paste")
        self.upload_rule_build()

        rule_builder = self.components.rule_builder
        rule_builder._.wait_for_and_click()
        self.screenshot("rules_deferred_list_2_rules_landing")

        self.rule_builder_filter_count(1)

        self.rule_builder_set_mapping("url-deferred", "J")
        self.rule_builder_set_extension("sra")
        self.scroll_to_end_of_table()
        self.screenshot("rules_deferred_list_3_end_of_table")
        self.rule_builder_add_regex_groups("L", 1, r"([^\d]+)\d+", screenshot_name="rules_deferred_list_4_regex")
        self.rule_builder_set_mapping(
            "list-identifiers", ["M", "A"], screenshot_name="rules_deferred_list_5_multiple_identifiers_edit"
        )
        self.scroll_to_end_of_table()
        self.screenshot("rules_deferred_list_6_multiple_identifiers")
        self.rule_builder_set_collection_name("PRJNA355367")
        self.screenshot("rules_deferred_list_7_named")
        rule_builder.main_button_ok.wait_for_and_click()
        hid = 2
        self.history_panel_wait_for_hid_state(hid, state="deferred", allowed_force_refreshes=1)
        self.screenshot("rules_deferred_list_7_download_complete")

    # @selenium_test
    # def test_rules_example_5_matching_collections(self):
    #    self.rule_builder_add_value("Protein FASTA")
    #     self.rule_builder_add_value("gff")
    #    self.rule_builder_add_value("Protein GFF")
