from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from galaxy.selenium.navigates_galaxy_mixin import NavigatesGalaxyMixin
from ..data import get_example_path

# Convenience constants for workbook examples
WORKBOOK_EXAMPLE_1 = get_example_path("workbook_example_1.tsv")
WORKBOOK_EXAMPLE_2 = get_example_path("workbook_example_2.tsv")
WORKBOOK_EXAMPLE_3 = get_example_path("workbook_example_3.tsv")
WORKBOOK_EXAMPLE_4 = get_example_path("workbook_example_4.tsv")

RULES_EXAMPLE_2_SOURCE = get_example_path("PRJDA60709.tsv")
RULES_EXAMPLE_3_SOURCE = get_example_path("PRJDB3920.tsv")
RULES_UNIPROT_SOURCE = get_example_path("uniprot.tsv")
RULES_UNIPROT_RULES = get_example_path("uniprot.json")
RULES_EXAMPLE_6_SOURCE = get_example_path("PRJNA355367.tsv")

# Screenshot captions (used multiple times)
CAPTION_RULES_WIZARD = "The Rules-based Data Import wizard interface"
CAPTION_COLLECTIONS_BUTTON = "The collections button highlighted to indicate collection mode is active"

# Documentation strings (used multiple times)
DOC_CLICK_RULES_ACTIVITY = """
Click the "Rules-based Data Import" activity to begin data import.
"""

DOC_CREATE_COLLECTIONS = """
For this example, we'll create a collection rather than individual datasets. Click the large 'collections' button to indicate that we want to build a collection. The button will remain highlighted to show that collection mode is active.
"""


class UploadStoriesMixin(NavigatesGalaxyMixin):
    """Mixin describing upload user stories around the workbooks and rules."""

    def upload_workbook_example_1(self):
        """Importing datasets from a workbook with automatic column mapping.

        Demonstrates that Galaxy can:
        - Automatically infer column mappings from common header patterns
        - Detect dataset name, URL, and genome (dbkey) columns
        - Correctly map columns without manual rule builder configuration
        """
        self.home()
        self.document(
            """
## Example 1: Uploading Simple Datasets with Automatic Metadata Detection

In this first example, we'll upload a set of FASTQ sequencing files from a spreadsheet. Galaxy's auto-detection feature will automatically recognize the column headers and map them to the appropriate metadata fields without any manual configuration.

This is the easiest way to upload multiple datasets when your spreadsheet has clear, recognizable column names.
"""
        )
        self.document(DOC_CLICK_RULES_ACTIVITY)
        self.click_rules_activity()
        self.screenshot("workbook_example_1_landing", CAPTION_RULES_WIZARD)

        self.document_file(WORKBOOK_EXAMPLE_1, "Example workbook with dataset name, URL, and genome columns")
        self.workbook_upload(WORKBOOK_EXAMPLE_1)

        self.document(
            """
Galaxy has automatically detected the column mappings based on the header names:
- The **name** column is recognized as the dataset name
- The **url** column is identified as the download URL for each file
- The **genome** column is mapped to the reference genome (also called build or dbkey)

Notice that we didn't have to configure any rules manually - Galaxy recognized these standard column patterns and set up the import automatically. This is perfect for straightforward data uploads where you have clear metadata in your spreadsheet.
"""
        )
        self.screenshot(
            "workbook_example_1_mapped",
            "The rule builder showing automatically detected column mappings for name, URL, and genome",
        )

    def upload_workbook_example_2(self):
        """Importing a simple list collection from a workbook.

        Demonstrates that Galaxy can:
        - Detect collection mode when user clicks "collections" button
        - Automatically infer list identifiers and file types
        - Map URL columns for collection elements
        """
        self.home()
        self.document(
            """
## Example 2: Creating a Simple List Collection

Building on the previous example, we'll now create a **list collection** - a way to group related datasets together. Collections are useful when you want to run the same analysis on multiple samples at once.

The key difference here is that our spreadsheet includes a **LIST IDENTIFIER** column, which tells Galaxy how to name each element in the collection.
"""
        )
        self.document(DOC_CLICK_RULES_ACTIVITY)
        self.click_rules_activity()
        self.screenshot("workbook_example_2_landing", CAPTION_RULES_WIZARD)

        self.document(DOC_CREATE_COLLECTIONS)
        self.components.rule_builder.create_collections.wait_for_and_click()
        self.screenshot("workbook_example_2_create_collections", CAPTION_COLLECTIONS_BUTTON)

        self.document_file(
            WORKBOOK_EXAMPLE_2,
            "Example workbook with list identifier, URL, and file type columns",
        )
        self.workbook_upload(WORKBOOK_EXAMPLE_2)

        self.document(
            """
Galaxy has recognized the column structure for a list collection:
- The **LIST IDENTIFIER** column is detected as the collection element identifiers
- The **URI** column (another common name for URLs) is mapped to the download locations
- The **TYPE** column specifies the file type (datatype) for each dataset

Even though these column names are different from Example 1 (URI instead of url, TYPE instead of format), Galaxy's auto-detection is flexible enough to recognize these alternative naming patterns. This means your spreadsheets don't need to follow one rigid format.
"""
        )
        self.screenshot(
            "workbook_example_2_mapped",
            "The rule builder showing automatically detected list identifier, URI, and type column mappings",
        )

    def upload_workbook_example_3(self):
        """Importing a list of pairs collection with automatic pairing.

        This test validates that Galaxy can:
        - Detect paired data from two URL columns per row
        - Automatically split and pair forward/reverse elements
        - Add paired_identifier column for the rule builder
        - Map list identifiers and genome information
        """
        self.home()
        self.document(
            """
## Example 3: Paired-End Sequencing Data

Many sequencing experiments produce **paired-end reads** - two files per sample (forward and reverse reads). Galaxy can automatically detect this structure when your spreadsheet has two URL columns per row.

This example demonstrates how Galaxy splits the paired data and creates a **list of pairs collection** - the appropriate structure for paired-end sequencing data.
"""
        )
        self.document(DOC_CLICK_RULES_ACTIVITY)
        self.click_rules_activity()
        self.screenshot("workbook_example_3_landing", CAPTION_RULES_WIZARD)

        self.document(DOC_CREATE_COLLECTIONS)
        self.components.rule_builder.create_collections.wait_for_and_click()
        self.screenshot("workbook_example_3_create_collections", CAPTION_COLLECTIONS_BUTTON)

        self.document_file(
            WORKBOOK_EXAMPLE_3,
            "Example workbook with paired URLs (forward/reverse reads) and genome information",
        )
        self.workbook_upload(WORKBOOK_EXAMPLE_3)

        self.document(
            """
Galaxy has automatically detected and processed the paired data structure:
- The **forward_url** and **reverse_url** columns are recognized as paired data (two URLs per sample)
- Galaxy automatically **split the data** - notice that each row in the spreadsheet becomes two rows in the rule builder
- A new **paired identifier** column (column 4) has been added automatically, marking which reads are "forward" and "reverse"
- The **list identifier** column defines the sample names
- The **genome** column provides the reference build for each sample

This automatic splitting and pairing is one of the most powerful features of the rule-based uploader - it handles the complexity of paired data without requiring manual rule configuration.
"""
        )
        self.screenshot(
            "workbook_example_3_mapped",
            "The rule builder showing automatic paired data detection - notice the data has been split with forward/reverse identifiers added",
        )

    def upload_workbook_example_4(self):
        """Importing nested list structures with paired data

        Demonstrates that Galaxy can:
        - Handle complex nested list structures
        - Detect and split paired data (two URLs per row)
        - Infer multiple list identifier levels
        - Build correct nested collection hierarchy

        Note: The outer list identifier is always the first one that appears.
        Column order matters for list nesting.
        """
        self.home()
        self.document(
            """
## Example 4: Nested Collections with Paired Data

For complex experiments, you might need **nested collections** - collections within collections. A common example is organizing paired-end data by experimental condition (e.g., different ChIP-seq targets) with technical replicates.

This example shows how Galaxy automatically builds nested structures when your spreadsheet has multiple identifier columns. **The key concept**: column order determines the nesting hierarchy.
"""
        )
        self.document(DOC_CLICK_RULES_ACTIVITY)
        self.click_rules_activity()
        self.screenshot("workbook_example_4_landing", CAPTION_RULES_WIZARD)

        self.document(DOC_CREATE_COLLECTIONS)
        self.components.rule_builder.create_collections.wait_for_and_click()
        self.screenshot("workbook_example_4_create_collections", CAPTION_COLLECTIONS_BUTTON)

        self.document_file(
            WORKBOOK_EXAMPLE_4,
            "Example workbook with paired URLs and multiple list identifier columns",
        )
        self.workbook_upload(WORKBOOK_EXAMPLE_4)

        self.document(
            """
Galaxy has detected a complex nested structure from the spreadsheet:
- The **URI 1** and **URI 2** columns are recognized as paired data and automatically split
- The **Outer List Identifier** and **Inner List Identifier** columns create a nested list structure
- The result is a **list of lists of pairs** collection - perfect for organizing paired-end data by experimental groups

**Important**: Column order determines the nesting hierarchy. The **third column** (labeled "Outer List Identifier") becomes the outer level, and the **fourth column** (labeled "Inner List Identifier") becomes the inner level. This is based purely on column position, not the column names.

If we had swapped the order of these columns in the spreadsheet (putting "Inner List Identifier" in column 3), that column would actually become the outer level - the labels in the headers don't affect the structure, only the column order matters.

This example demonstrates the most advanced capability of auto-detection, handling complex hierarchical data structures that are common in large sequencing studies.
"""
        )
        self.screenshot(
            "workbook_example_4_mapped",
            "The rule builder showing automatic nested structure detection from multiple list identifier columns and paired URL columns",
        )

    def upload_rules_example_1(self):
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
        self.wait_for_upload_modal()
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
        filter_input = filter_editor_element.find_element(By.CSS_SELECTOR, "input[type='number']")
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

    def upload_rules_example_2(self):
        self.perform_upload(RULES_EXAMPLE_2_SOURCE)
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

    def upload_rules_example_3(self):
        self.perform_upload(RULES_EXAMPLE_3_SOURCE)
        self.history_panel_wait_for_hid_ok(1)
        self.upload_rule_start()
        self.upload_rule_set_data_type("Collections")
        self.upload_rule_dataset_dialog()
        self.upload_rule_set_dataset(1)
        self.wait_for_upload_modal()
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

    def upload_rules_example_4(self):
        # http://www.uniprot.org/uniprot/?query=proteome:UP000052092+AND+proteomecomponent:%22Genome%22
        self.setup_uniprot_example()
        self.wait_for_upload_modal()
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

        self.screenshot("rules_example_4_8_source")

        rule_builder.main_button_ok.wait_for_and_click()
        rule_builder.view_source.wait_for_visible()

    def upload_rules_example_5(self):
        self.setup_uniprot_example()
        self.wait_for_upload_modal()
        self.screenshot("rules_example_5_1_inputs")
        self.upload_rule_build()

        rule_builder = self.components.rule_builder
        rule_builder.view_source.wait_for_and_click()

        with open(RULES_UNIPROT_RULES) as f:
            content = f.read()
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
        self.scroll_to_end_of_table()
        self.screenshot("rules_example_5_6_presplit")
        self.rule_builder_split_columns(
            ["C", "D", "E"], ["F", "G", "H"], screenshot_name="rules_example_5_7_split_columns"
        )
        self.screenshot("rules_example_5_8_split")
        self.rule_builder_set_mapping("file-type", "D")
        self.rule_builder_set_mapping("collection-name", "E")
        self.screenshot("rules_example_5_9_mapping")

    def upload_rules_example_6(self):
        self.home()
        self.perform_upload(RULES_EXAMPLE_6_SOURCE)
        self.history_panel_wait_for_hid_ok(1)
        self.upload_rule_start()
        self.upload_rule_set_data_type("Collections")
        self.upload_rule_dataset_dialog()
        self.upload_rule_set_dataset(1)

        self.wait_for_upload_modal()
        self.screenshot("rules_example_6_1_paste")
        self.upload_rule_build()

        rule_builder = self.components.rule_builder
        rule_builder._.wait_for_and_click()

        self.screenshot("rules_example_6_2_rules_landing")

        self.rule_builder_filter_count(1)

        self.rule_builder_set_mapping("url", "J")
        self.rule_builder_set_extension("sra")
        self.scroll_to_end_of_table()
        self.screenshot("rules_example_6_3_end_of_table")
        self.rule_builder_add_regex_groups("L", 1, r"([^\d]+)\d+", screenshot_name="rules_example_6_4_regex")
        self.rule_builder_set_mapping(
            "list-identifiers", ["M", "A"], screenshot_name="rules_example_6_5_multiple_identifiers_edit"
        )
        self.scroll_to_end_of_table()
        self.screenshot("rules_example_6_6_multiple_identifiers")
        self.rule_builder_set_collection_name("PRJNA355367")
        self.screenshot("rules_example_6_7_named")

    def setup_uniprot_example(self):
        self.perform_upload(RULES_UNIPROT_SOURCE)
        self.history_panel_wait_for_hid_ok(1)
        self.upload_rule_start()
        self.upload_rule_set_data_type("Collections")
        self.upload_rule_dataset_dialog()
        self.upload_rule_set_dataset(1)

    def scroll_to_end_of_table(self):
        if self.backend_type == "selenium":
            rule_builder = self.components.rule_builder
            table_elem = rule_builder.table.wait_for_visible()
            # handsontable
            # first_cell = table_elem.find_elements(By.CSS_SELECTOR, "td")[0]
            # aggrid
            first_cell = table_elem.find_elements(By.CSS_SELECTOR, ".ag-cell")[0]
            action_chains = self.action_chains()
            action_chains.move_to_element(first_cell)
            action_chains.click(first_cell)
            for _ in range(15):
                action_chains.send_keys(Keys.ARROW_RIGHT)
            action_chains.perform()
