import os

import pytest

from .framework import (
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)


class TestUploads(SeleniumTestCase, UsesHistoryItemAssertions):
    @selenium_test
    def test_upload_file(self):
        self.perform_upload(self.get_filename("1.sam"))

        self.history_panel_wait_for_hid_ok(1)
        history_count = len(self.history_contents())
        assert history_count == 1, "Incorrect number of items in history - expected 1, found %d" % history_count

        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_summary_includes(1, "28 lines")

    @selenium_test
    def test_upload_pasted_content(self):
        pasted_content = "this is pasted"
        self.perform_upload_of_pasted_content(pasted_content)

        self.history_panel_wait_for_hid_ok(1)
        history_count = len(self.history_contents())
        assert history_count == 1, "Incorrect number of items in history - expected 1, found %d" % history_count

    @selenium_test
    def test_upload_pasted_url_content(self):
        pasted_content = "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/LICENSE.txt"
        self.perform_upload_of_pasted_content(pasted_content)

        self.history_panel_wait_for_hid_ok(1)
        history_count = len(self.history_contents())
        assert history_count == 1, "Incorrect number of items in history - expected 1, found %d" % history_count

    @selenium_test
    def test_upload_composite_dataset_pasted_data(self):
        paste_content = ["a", "b", "c"]
        self.perform_upload_of_composite_dataset_pasted_data("velvet", paste_content)

        self.history_panel_wait_for_hid_ok(1)
        history_count = len(self.history_contents())
        assert history_count == 1, "Incorrect number of items in history - expected 1, found %d" % history_count

        self.history_panel_click_item_title(hid=1, wait=True)
        self.history_panel_item_view_dataset_details(1)
        param_values = self.driver.find_elements(self.by.CSS_SELECTOR, "#tool-parameters td.tool-parameter-value")
        request_json = param_values[1].text
        for data in paste_content:
            assert f'"paste_content": "{data}"' in request_json

    @selenium_test
    def test_upload_simplest(self):
        self.perform_upload(self.get_filename("1.sam"))

        self.history_panel_wait_for_hid_ok(1)
        history_contents = self.history_contents()
        history_count = len(history_contents)
        assert history_count == 1, "Incorrect number of items in history - expected 1, found %d" % history_count

        hda = history_contents[0]
        assert hda["name"] == "1.sam", hda
        assert hda["extension"] == "sam", hda

        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_dbkey_displayed_as(1, "?")

    @selenium_test
    def test_upload_specify_ext(self):
        self.perform_upload(self.get_filename("1.sam"), ext="txt")
        self.history_panel_wait_for_hid_ok(1)
        history_contents = self.history_contents()
        hda = history_contents[0]
        assert hda["name"] == "1.sam"
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
        history_contents = self.history_contents()
        hda = history_contents[0]
        assert hda["name"] == "1.sam"
        assert hda["extension"] == "txt", hda

    @selenium_test
    def test_upload_specify_genome_all(self):
        self.perform_upload(self.get_filename("1.sam"), genome_all="hg18")
        self.history_panel_wait_for_hid_ok(1)

        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_dbkey_displayed_as(1, "hg18")

    @selenium_test
    def test_upload_deferred(self):
        self.perform_upload_of_pasted_content(
            "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed", deferred=True
        )
        hid = 1
        self.history_panel_wait_for_hid_deferred(hid)
        self.history_panel_click_item_title(hid=hid, wait=True)
        self.screenshot("history_panel_dataset_deferred")

    @selenium_test
    def test_upload_list(self):
        self.upload_list([self.get_filename("1.tabular")], name="Test List")
        self.history_panel_wait_for_hid_ok(3)
        # Make sure modals disappeared - both List creator (TODO: upload).
        self.wait_for_selector_absent_or_hidden(".collection-creator")

        self.assert_item_name(3, "Test List")

        # Make sure source item is hidden when the collection is created.
        self.history_panel_wait_for_hid_hidden(1)

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

    @selenium_test
    @pytest.mark.gtn_screenshot
    @pytest.mark.local
    def test_rules_example_1_datasets(self):
        # Test case generated for:
        #   https://www.ebi.ac.uk/ena/data/view/PRJDA60709
        self.home()
        self.upload_rule_start()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("rules_example_1_1_rules_landing")
        self.components.upload.rule_source_content.wait_for_and_send_keys(
            """study_accession sample_accession    experiment_accession    fastq_ftp
PRJDA60709  SAMD00016379    DRX000475   ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000770/DRR000770.fastq.gz
PRJDA60709  SAMD00016383    DRX000476   ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000771/DRR000771.fastq.gz
PRJDA60709  SAMD00016380    DRX000477   ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000772/DRR000772.fastq.gz
PRJDA60709  SAMD00016378    DRX000478   ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000773/DRR000773.fastq.gz
PRJDA60709  SAMD00016381    DRX000479   ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000774/DRR000774.fastq.gz
PRJDA60709  SAMD00016382    DRX000480   ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000775/DRR000775.fastq.gz"""
        )
        self._wait_for_upload_modal()
        self.screenshot("rules_example_1_2_paste")
        self.upload_rule_build()
        rule_builder = self.components.rule_builder
        rule_builder._.wait_for_and_click()
        self.screenshot("rules_example_1_3_initial_rules")
        rule_builder.menu_button_filter.wait_for_and_click()
        self.screenshot("rule_builder_filters")
        rule_builder.menu_item_rule_type(rule_type="add-filter-count").wait_for_and_click()
        filter_editor = rule_builder.rule_editor(rule_type="add-filter-count")
        filter_editor_element = filter_editor.wait_for_visible()
        filter_input = filter_editor_element.find_element(self.by.CSS_SELECTOR, "input[type='number']")
        filter_input.clear()
        filter_input.send_keys("1")
        self.screenshot("rules_example_1_4_filter_header")
        rule_builder.rule_editor_ok.wait_for_and_click()
        self.rule_builder_set_mapping("url", "D")
        self.rule_builder_set_mapping("name", "C", screenshot_name="rules_example_1_5_mapping_edit")
        self.screenshot("rules_example_1_6_mapping_set")
        self.rule_builder_set_extension("fastqsanger.gz")
        self.screenshot("rules_example_1_7_extension_set")
        # rule_builder.main_button_ok.wait_for_and_click()
        # self.history_panel_wait_for_hid_ok(6)
        # self.screenshot("rules_example_1_6_download_complete")

    @selenium_test
    @pytest.mark.gtn_screenshot
    @pytest.mark.local
    def test_rules_example_2_list(self):
        self.perform_upload(self.get_filename("rules/PRJDA60709.tsv"))
        self.history_panel_wait_for_hid_ok(1)
        self.upload_rule_start()
        self.upload_rule_set_data_type("Collections")
        self.upload_rule_dataset_dialog()
        self.upload_rule_set_dataset(1)
        self.screenshot("rules_example_2_1_inputs")
        self.upload_rule_build()
        rule_builder = self.components.rule_builder
        rule_builder._.wait_for_and_click()
        self.screenshot("rules_example_2_2_initial_rules")
        # Filter header.
        self.rule_builder_filter_count(1)
        self.rule_builder_set_mapping("url", "D")
        self.rule_builder_set_mapping("list-identifiers", "C")
        self.rule_builder_set_extension("fastqsanger.gz")
        self.screenshot("rules_example_2_3_rules")
        self.rule_builder_set_collection_name("PRJDA60709")
        self.screenshot("rules_example_2_4_name")
        # rule_builder.main_buton_ok.wait_for_and_click()
        # self.history_panel_wait_for_hid_ok(2)
        # self.screenshot("rules_example_2_5_download_complete")

    @selenium_test
    @pytest.mark.gtn_screenshot
    @pytest.mark.local
    def test_rules_example_3_list_pairs(self):
        self.perform_upload(self.get_filename("rules/PRJDB3920.tsv"))
        self.history_panel_wait_for_hid_ok(1)
        self.upload_rule_start()
        self.upload_rule_set_data_type("Collections")
        self.upload_rule_dataset_dialog()
        self.upload_rule_set_dataset(1)
        self._wait_for_upload_modal()
        self.screenshot("rules_example_3_1_inputs")
        self.upload_rule_build()
        rule_builder = self.components.rule_builder
        rule_builder._.wait_for_and_click()
        self.screenshot("rules_example_3_2_initial_rules")
        # Filter header.
        self.rule_builder_filter_count(1)
        self.rule_builder_set_mapping("list-identifiers", "C")
        self.rule_builder_set_extension("fastqsanger.gz")
        self.screenshot("rules_example_3_3_old_rules")
        self.rule_builder_add_regex_groups("D", 2, r"(.*);(.*)", screenshot_name="rules_example_3_4_regex")
        self.screenshot("rules_example_3_6_with_regexes")
        # Remove A also?
        self.rule_builder_remove_columns(["D"], screenshot_name="rules_example_3_7_removed_column")
        self.rule_builder_split_columns(["D"], ["E"], screenshot_name="rules_example_3_8_split_columns")
        self.screenshot("rules_example_3_9_columns_are_split")
        self.rule_builder_add_regex_groups(
            "D", 1, r".*_(\d).fastq.gz", screenshot_name="rules_example_3_10_regex_paired"
        )
        self.screenshot("rules_example_3_11_has_paired_id")
        self.rule_builder_swap_columns("D", "E", screenshot_name="rules_example_3_12_swap_columns")
        self.screenshot("rules_example_3_13_swapped_columns")
        self.rule_builder_set_mapping("paired-identifier", "D")
        self.rule_builder_set_mapping("url", "E")
        self.rule_builder_set_collection_name("PRJDB3920")
        self.screenshot("rules_example_3_14_paired_identifier_set")

    @selenium_test
    @pytest.mark.gtn_screenshot
    @pytest.mark.local
    def test_rules_example_4_accessions(self):
        # http://www.uniprot.org/uniprot/?query=proteome:UP000052092+AND+proteomecomponent:%22Genome%22
        self._setup_uniprot_example()
        self._wait_for_upload_modal()
        self.screenshot("rules_example_4_1_inputs")
        self.upload_rule_build()
        rule_builder = self.components.rule_builder
        rule_builder._.wait_for_and_click()
        self.screenshot("rules_example_4_2_initial_rules")
        self.rule_builder_filter_count(1)
        self.rule_builder_remove_columns(["B", "C", "E", "F", "G"])
        self.rule_builder_set_mapping("info", "B")
        self.screenshot("rules_example_4_3_basic_rules")
        self.rule_builder_sort("A", screenshot_name="rules_example_4_4_sort")

        self.rule_builder_add_regex_replacement(
            "A", ".*", "http://www.uniprot.org/uniprot/\\0.fasta", screenshot_name="rules_example_4_5_url"
        )
        self.screenshot("rules_example_4_6_url_built")
        self.rule_builder_set_mapping("list-identifiers", "A")
        self.rule_builder_set_mapping("url", "C")
        self.rule_builder_set_extension("fasta")
        self.rule_builder_set_collection_name("UP000052092")
        self.screenshot("rules_example_4_7_mapping_extension_and_name")

        rule_builder.view_source.wait_for_and_click()
        text_area_elem = rule_builder.source.wait_for_visible()

        self.screenshot("rules_example_4_8_source")
        self.write_screenshot_directory_file("rules_example_4_8_text", text_area_elem.get_attribute("value"))

        rule_builder.main_button_ok.wait_for_and_click()
        rule_builder.view_source.wait_for_visible()

    @selenium_test
    @pytest.mark.gtn_screenshot
    @pytest.mark.local
    def test_rules_example_5_matching_collections(self):
        self._setup_uniprot_example()
        self._wait_for_upload_modal()
        self.screenshot("rules_example_5_1_inputs")
        self.upload_rule_build()

        rule_builder = self.components.rule_builder
        rule_builder.view_source.wait_for_and_click()

        content = self._read_rules_test_data_file("uniprot.json")
        self.rule_builder_enter_source_text(content)
        self.screenshot("rules_example_5_2_source")
        rule_builder.main_button_ok.wait_for_and_click()
        rule_builder.view_source.wait_for_visible()
        self.screenshot("rules_example_5_3_initial_rules")
        self.rule_builder_add_value("fasta", screenshot_name="rules_example_5_4_fasta")
        self.rule_builder_add_value("UP000052092 FASTA")
        self.rule_builder_add_regex_replacement(
            "A", ".*", "http://www.uniprot.org/uniprot/\\0.gff", screenshot_name="rules_example_5_5_url"
        )
        self.rule_builder_add_value("gff3")
        self.rule_builder_add_value("UP000052092 GFF3")
        self._scroll_to_end_of_table()
        self.screenshot("rules_example_5_6_presplit")
        self.rule_builder_split_columns(
            ["C", "D", "E"], ["F", "G", "H"], screenshot_name="rules_example_5_7_split_columns"
        )
        self.screenshot("rules_example_5_8_split")
        self.rule_builder_set_mapping("file-type", "D")
        self.rule_builder_set_mapping("collection-name", "E")
        self.screenshot("rules_example_5_9_mapping")

    @selenium_test
    @pytest.mark.gtn_screenshot
    @pytest.mark.local
    def test_rules_example_6_nested_lists(self):
        self.home()
        self.perform_upload(self.get_filename("rules/PRJNA355367.tsv"))
        self.history_panel_wait_for_hid_ok(1)
        self.upload_rule_start()
        self.upload_rule_set_data_type("Collections")
        self.upload_rule_dataset_dialog()
        self.upload_rule_set_dataset(1)

        self._wait_for_upload_modal()
        self.screenshot("rules_example_6_1_paste")
        self.upload_rule_build()

        rule_builder = self.components.rule_builder
        rule_builder._.wait_for_and_click()

        self.screenshot("rules_example_6_2_rules_landing")

        self.rule_builder_filter_count(1)

        self.rule_builder_set_mapping("url", "J")
        self.rule_builder_set_extension("sra")
        self._scroll_to_end_of_table()
        self.screenshot("rules_example_6_3_end_of_table")
        self.rule_builder_add_regex_groups("L", 1, r"([^\d]+)\d+", screenshot_name="rules_example_6_4_regex")
        self.rule_builder_set_mapping(
            "list-identifiers", ["M", "A"], screenshot_name="rules_example_6_5_multiple_identifiers_edit"
        )
        self._scroll_to_end_of_table()
        self.screenshot("rules_example_6_6_multiple_identifiers")
        self.rule_builder_set_collection_name("PRJNA355367")
        self.screenshot("rules_example_6_7_named")

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
        self._wait_for_upload_modal()
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
        filter_input = filter_editor_element.find_element(self.by.CSS_SELECTOR, "input[type='number']")
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

    @selenium_test
    @pytest.mark.local
    def test_rules_deferred_list(self):
        self.home()
        self.perform_upload(self.get_filename("rules/PRJNA355367.tsv"))
        self.history_panel_wait_for_hid_ok(1)
        self.upload_rule_start()
        self.upload_rule_set_data_type("Collections")
        self.upload_rule_dataset_dialog()
        self.upload_rule_set_dataset(1)

        self._wait_for_upload_modal()
        self.screenshot("rules_deferred_list_1_paste")
        self.upload_rule_build()

        rule_builder = self.components.rule_builder
        rule_builder._.wait_for_and_click()
        self.screenshot("rules_deferred_list_2_rules_landing")

        self.rule_builder_filter_count(1)

        self.rule_builder_set_mapping("url-deferred", "J")
        self.rule_builder_set_extension("sra")
        self._scroll_to_end_of_table()
        self.screenshot("rules_deferred_list_3_end_of_table")
        self.rule_builder_add_regex_groups("L", 1, r"([^\d]+)\d+", screenshot_name="rules_deferred_list_4_regex")
        self.rule_builder_set_mapping(
            "list-identifiers", ["M", "A"], screenshot_name="rules_deferred_list_5_multiple_identifiers_edit"
        )
        self._scroll_to_end_of_table()
        self.screenshot("rules_deferred_list_6_multiple_identifiers")
        self.rule_builder_set_collection_name("PRJNA355367")
        self.screenshot("rules_deferred_list_7_named")
        rule_builder.main_button_ok.wait_for_and_click()
        hid = 2
        self.history_panel_wait_for_hid_ok(hid)
        self.screenshot("rules_deferred_list_7_download_complete")

    def _read_rules_test_data_file(self, name):
        with open(self.test_data_resolver.get_filename(os.path.join("rules", name))) as f:
            return f.read()

    def _wait_for_upload_modal(self):
        self.components.upload.build_button.wait_for_visible()
        self.components.upload.build_button.wait_for_clickable()

    def _scroll_to_end_of_table(self):
        rule_builder = self.components.rule_builder
        table_elem = rule_builder.table.wait_for_visible()
        first_cell = table_elem.find_elements(self.by.CSS_SELECTOR, "td")[0]
        action_chains = self.action_chains()
        action_chains.move_to_element(first_cell)
        action_chains.click(first_cell)
        for _ in range(15):
            action_chains.send_keys(self.keys.ARROW_RIGHT)
        action_chains.perform()

    def _setup_uniprot_example(self):
        self.perform_upload(self.get_filename("rules/uniprot.tsv"))
        self.history_panel_wait_for_hid_ok(1)
        self.upload_rule_start()
        self.upload_rule_set_data_type("Collections")
        self.upload_rule_dataset_dialog()
        self.upload_rule_set_dataset(1)

    # @selenium_test
    # def test_rules_example_5_matching_collections(self):
    #    self.rule_builder_add_value("Protein FASTA")
    #     self.rule_builder_add_value("gff")
    #    self.rule_builder_add_value("Protein GFF")
