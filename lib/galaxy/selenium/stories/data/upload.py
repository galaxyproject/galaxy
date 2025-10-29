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

    def upload_workbook_example_1(self, include_result: bool = False):
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
        if include_result:
            rule_builder = self.components.rule_builder
            rule_builder.wizard_import.wait_for_and_click()
            self.history_panel_wait_for_hid_ok(4)
            # In next iteration - wait on the "uploading" message to disappear.
            self.sleep_for(self.wait_types.UX_RENDER)
            self.screenshot("workbook_example_1_complete", "Final datasets created and available in the history.")

    def upload_workbook_example_2(self, include_result: bool = False):
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
        self.rule_builder_set_collection_name("Example 2 - List")
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
        if include_result:
            self.rule_builder_import()
            self.history_panel_wait_for_hid_ok(1)
            # In next iteration - wait on the "uploading" message to disappear.
            self.sleep_for(self.wait_types.UX_RENDER)
            self.screenshot("workbook_example_2_complete", "Final collection created and available in the history.")

    def upload_workbook_example_3(self, include_result: bool = False):
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
        self.rule_builder_set_collection_name("Example 3 - A List of Pairs")

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
        if include_result:
            self.rule_builder_import()
            self.history_panel_wait_for_hid_ok(1)
            # In next iteration - wait on the "uploading" message to disappear.
            self.sleep_for(self.wait_types.UX_RENDER)
            self.screenshot("workbook_example_3_complete", "Final collection created and available in the history.")

    def upload_workbook_example_4(self, include_result: bool = False):
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
        self.rule_builder_set_collection_name("Example 4 - Nested Collections")

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
        # This is 12 multi-gigabyte datasets - don't both ever actually running the upload in
        # this example.

    def upload_rules_example_1(self, include_result: bool = False):
        """Uploading datasets with manual rules - basic filtering and column mapping.

        Demonstrates manual rule building to:
        - Filter header rows from tabular data
        - Map columns to dataset names and URLs
        - Set file types explicitly
        """
        self.home()
        self.document(
            """
## Uploading Datasets with Rules

This example demonstrates the fundamental workflow of the rule-based uploader when working with tabular metadata from external sources like the [European Nucleotide Archive (ENA)](https://www.ebi.ac.uk/ena).

We'll take a table containing study metadata with multiple columns and transform it into Galaxy datasets by:
1. **Filtering out header rows** that don't contain downloadable data
2. **Mapping columns** to tell Galaxy which column contains the dataset name and which contains the download URL
3. **Setting the file type** so Galaxy knows how to handle the data

This workflow is common when you've downloaded metadata from a sequence repository or generated it from your own LIMS system.
"""
        )
        self.upload_rule_start()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("rules_example_1_1_rules_landing", "The rule-based upload dialog")
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
        self.screenshot("rules_example_1_2_paste", "Tabular data pasted into the upload dialog")
        self.document(
            """
After pasting the tabular data, we click **Build** to open the rule builder interface. This opens a spreadsheet-like view where we can see our data and define rules to transform it.
"""
        )
        self.upload_rule_build()
        rule_builder = self.components.rule_builder
        rule_builder._.wait_for_and_click()
        self.screenshot("rules_example_1_3_initial_rules", "The rule builder showing the initial tabular data")
        self.document(
            """
### Filtering the Header Row

Our first task is to remove the header row (the first row containing column names) since it doesn't represent actual data to download. We'll use a **Filter** rule to remove it.

Galaxy's rule builder provides various filter options - in this case, we'll filter out the first N rows (where N=1).
"""
        )
        rule_builder.menu_button_filter.wait_for_and_click()
        self.screenshot("rule_builder_filters", "The Filter menu showing available filtering options")
        rule_builder.menu_item_rule_type(rule_type="add-filter-count").wait_for_and_click()
        filter_editor = rule_builder.rule_editor(rule_type="add-filter-count")
        filter_editor_element = filter_editor.wait_for_visible()
        filter_input = filter_editor_element.find_element(By.CSS_SELECTOR, "input[type='number']")
        filter_input.clear()
        filter_input.send_keys("1")
        self.screenshot("rules_example_1_4_filter_header", "Configuring the filter to remove the first row")
        self.document(
            """
After applying the filter, the header row is removed and we're left with only the data rows. Now we need to tell Galaxy how to interpret each column.
"""
        )
        rule_builder.rule_editor_ok.wait_for_and_click()
        self.document(
            """
### Defining Column Mappings

Next, we define **column definitions** to tell Galaxy:
- Which column contains the **URL** (where to download files from)
- Which column contains the **Name** (what to call each dataset in the history)

In this example:
- Column D (fastq_ftp) contains the download URLs
- Column C (experiment_accession) will be used as the dataset names
"""
        )
        self.rule_builder_set_mapping("url", "D")
        self.rule_builder_set_mapping("name", "C", screenshot_name="rules_example_1_5_mapping_edit")
        self.screenshot("rules_example_1_6_mapping_set", "Column mappings set for URL and Name")
        self.document(
            """
Finally, we specify the **file type** (datatype extension) so Galaxy knows these are compressed FASTQ files. This determines how Galaxy will process and display the data.
"""
        )
        self.rule_builder_set_extension("fastqsanger.gz")
        self.screenshot("rules_example_1_7_extension_set", "File type set to fastqsanger.gz - ready to upload")
        if include_result:
            rule_builder.main_button_ok.wait_for_and_click()
            self.history_panel_wait_for_hid_ok(6)
            self.screenshot(
                "rules_example_1_6_download_complete", "Final datasets created and available in the history."
            )

    def upload_rules_example_2(self, include_result: bool = False):
        """Creating a simple list collection from a history dataset.

        Demonstrates:
        - Using metadata from an existing history dataset as input
        - Creating collections instead of individual datasets
        - Defining list identifiers for collection elements
        """
        self.document(
            """
## Creating a Simple Dataset List Collection

Building on the previous example, we'll now create a **list collection** instead of individual datasets. Collections are powerful organizational structures in Galaxy that allow you to:
- Group related datasets together
- Run tools on all elements at once (mapping over collections)
- Maintain sample identifiers throughout your analysis

This example also demonstrates loading metadata from an **existing history dataset** rather than pasting it directly. This is useful when you've:
- Downloaded metadata from an external source as a file
- Generated sample lists using Galaxy tools
- Performed filtering or manipulation on your metadata
"""
        )
        self.perform_upload(RULES_EXAMPLE_2_SOURCE)
        self.history_panel_wait_for_hid_ok(1)
        self.upload_rule_start()
        self.upload_rule_set_data_type("Collections")
        self.upload_rule_dataset_dialog()
        self.upload_rule_set_dataset(1)
        self.screenshot(
            "rules_example_2_1_inputs", "Rule builder configured to create collections from a history dataset"
        )
        self.document(
            """
The key difference from Example 1 is that we've selected:
- **Upload data as**: Collections (instead of individual datasets)
- **Load tabular data from**: a History Dataset (instead of pasted text)

This tells Galaxy we want to build a collection structure from our metadata.
"""
        )
        self.upload_rule_build()
        rule_builder = self.components.rule_builder
        rule_builder._.wait_for_and_click()
        self.screenshot("rules_example_2_2_initial_rules", "Initial view of the rule builder with metadata loaded")
        self.document(
            """
### Collection-Specific Mappings

When creating collections, we use **List Identifier** instead of **Name** for our dataset labels. List identifiers serve as the element names within the collection and are preserved when you map tools over the collection.

We'll apply the same transformations as before:
1. Filter the header row
2. Map column D to URL (download location)
3. Map column C to **List Identifier** (collection element name)
4. Set the file type to fastqsanger.gz
"""
        )
        # Filter header.
        self.rule_builder_filter_count(1)
        self.rule_builder_set_mapping("url", "D")
        self.rule_builder_set_mapping("list-identifiers", "C")
        self.rule_builder_set_extension("fastqsanger.gz")
        self.screenshot("rules_example_2_3_rules", "Rules configured with list identifier mapping")
        self.document(
            """
Finally, we give the collection itself a name - this is the name that will appear in your history panel. Using the study accession (PRJDA60709) makes it easy to track which experiment this data came from.
"""
        )
        self.rule_builder_set_collection_name("PRJDA60709")
        self.screenshot("rules_example_2_4_name", "Collection named and ready to upload")
        if include_result:
            rule_builder.main_button_ok.wait_for_and_click()
            self.history_panel_wait_for_hid_ok(2)
            self.screenshot(
                "rules_example_2_5_download_complete", "Final collection created and available in the history."
            )

    def upload_rules_example_3(self, include_result: bool = False):
        """Creating a list of pairs collection with regular expressions.

        Demonstrates advanced techniques:
        - Using regular expressions to extract data from columns
        - Splitting columns to create multiple rows per sample
        - Creating paired-end collection structures
        - Building proper paired identifiers
        """
        self.document(
            """
## Creating a List of Dataset Pairs

Many sequencing experiments produce **paired-end reads** - two files per sample (forward and reverse). This example shows how to handle metadata where both URLs are in a single column, separated by a semicolon.

This is a more advanced workflow that demonstrates the power of the rule builder for data transformation. We'll need to:
1. **Split** the semicolon-separated URLs into separate columns
2. **Duplicate each row** so one row becomes two (one for forward, one for reverse)
3. **Extract** the pair indicator (1 or 2) from the filenames using regular expressions
4. **Map** the appropriate columns to create a list:paired collection structure

This type of transformation is common when working with data from repositories like ENA or SRA where paired files are often listed together.
"""
        )
        self.perform_upload(RULES_EXAMPLE_3_SOURCE)
        self.history_panel_wait_for_hid_ok(1)
        self.upload_rule_start()
        self.upload_rule_set_data_type("Collections")
        self.upload_rule_dataset_dialog()
        self.upload_rule_set_dataset(1)
        self.wait_for_upload_modal()
        self.screenshot("rules_example_3_1_inputs", "Loading paired-end data from a history dataset")
        self.upload_rule_build()
        rule_builder = self.components.rule_builder
        rule_builder._.wait_for_and_click()
        self.screenshot("rules_example_3_2_initial_rules", "Initial data showing semicolon-separated URLs in column D")
        self.document(
            """
### Initial Setup

First, we'll do our standard setup: filter the header and set the list identifier mapping. Notice that column D contains two URLs separated by a semicolon - we'll need to handle this specially.
"""
        )
        # Filter header.
        self.rule_builder_filter_count(1)
        self.rule_builder_set_mapping("list-identifiers", "C")
        self.rule_builder_set_extension("fastqsanger.gz")
        self.screenshot("rules_example_3_3_old_rules", "Basic mappings set, but column D still has two URLs")
        self.document(
            """
### Splitting URLs with Regular Expressions

Column D contains two URLs like `url1;url2`. We'll use a **regular expression** to split this into two separate columns:
- Pattern: `(.*);(.*)`
  - `(.*)` = capture any characters (first URL)
  - `;` = match the semicolon separator
  - `(.*)` = capture any characters (second URL)
- This creates two new columns (D and E) from the original column D
"""
        )
        self.rule_builder_add_regex_groups("D", 2, r"(.*);(.*)", screenshot_name="rules_example_3_4_regex")
        self.screenshot(
            "rules_example_3_6_with_regexes", "Column D split into two columns with forward and reverse URLs"
        )
        self.document(
            """
Now we have two URL columns, but they're still in the same row. We need one row per file.
"""
        )
        # Remove A also?
        self.rule_builder_remove_columns(["D"], screenshot_name="rules_example_3_7_removed_column")
        self.document(
            """
### Creating Rows for Each Pair Member

We'll use **Split Columns** to convert each row into two rows:
- Odd rows will keep column D (forward reads)
- Even rows will keep column E (reverse reads)

This effectively doubles our row count, with each original sample now represented by two rows.
"""
        )
        self.rule_builder_split_columns(["D"], ["E"], screenshot_name="rules_example_3_8_split_columns")
        self.screenshot(
            "rules_example_3_9_columns_are_split", "Each sample is now two rows - one for each read direction"
        )
        self.document(
            r"""
### Extracting the Pair Indicator

Now we need to tell Galaxy which rows are forward reads and which are reverse. The filenames contain `_1.fastq.gz` or `_2.fastq.gz`, so we'll extract that digit using another regular expression:
- Pattern: `.*_(\d).fastq.gz`
  - `.*_` = match everything up to the underscore
  - `(\d)` = capture one digit (this becomes our pair indicator: 1 or 2)
  - `.fastq.gz` = match the file extension
"""
        )
        self.rule_builder_add_regex_groups(
            "D", 1, r".*_(\d).fastq.gz", screenshot_name="rules_example_3_10_regex_paired"
        )
        self.screenshot("rules_example_3_11_has_paired_id", "New column showing 1 or 2 to indicate forward/reverse")
        self.document(
            """
For clarity, we'll swap the columns so the pair indicator appears before the URL column. Then we set our final column definitions:
- Column D: **Paired identifier** (1 for forward, 2 for reverse)
- Column E: **URL** (download location)
"""
        )
        self.rule_builder_swap_columns("D", "E", screenshot_name="rules_example_3_12_swap_columns")
        self.screenshot("rules_example_3_13_swapped_columns", "Columns reordered for clarity")
        self.rule_builder_set_mapping("paired-identifier", "D")
        self.rule_builder_set_mapping("url", "E")
        self.rule_builder_set_collection_name("PRJDB3920")
        self.screenshot("rules_example_3_14_paired_identifier_set", "Paired collection configured and ready to upload")

    def upload_rules_example_4(self, include_result: bool = False):
        """Building URLs from accession numbers.

        Demonstrates advanced URL construction:
        - Dynamically building download URLs from accession IDs
        - Using regex replacement to construct URLs
        - Sorting data for better organization
        - Viewing the JSON rule definitions
        """
        self.document(
            """
## Building URLs from Accession Information

In previous examples, our metadata already contained complete download URLs. But often you'll have **accession numbers** or **identifiers** without the full URLs. This example shows how to construct URLs programmatically from identifiers.

### Scenario: UniProt Protein Data

We have a table of UniProt accession IDs for proteins from a specific organism. UniProt provides FASTA files at predictable URLs:
- Pattern: `https://www.uniprot.org/uniprot/{accession}.fasta`
- Example: `https://www.uniprot.org/uniprot/E7C0H6.fasta`

We'll use the rule builder to:
1. Clean up unnecessary columns
2. **Build complete URLs** using regex replacement
3. Sort the data alphabetically for better organization
4. Map the accession IDs as list identifiers
"""
        )
        self.setup_uniprot_example()
        self.wait_for_upload_modal()
        self.screenshot("rules_example_4_1_inputs", "UniProt metadata loaded with accession IDs")
        self.upload_rule_build()
        rule_builder = self.components.rule_builder
        rule_builder._.wait_for_and_click()
        self.screenshot("rules_example_4_2_initial_rules", "Initial UniProt data with many columns")
        self.document(
            """
### Cleaning and Organizing the Data

First, we'll clean up our data by:
1. Filtering the header row
2. Removing unnecessary columns (keeping only accession ID and protein names)
3. Mapping the protein names to the **Info** field (this will appear as tooltip text in the history)
4. Sorting by accession ID for easier browsing
"""
        )
        self.rule_builder_filter_count(1)
        self.rule_builder_remove_columns(["B", "C", "E", "F", "G"])
        self.rule_builder_set_mapping("info", "B")
        self.screenshot("rules_example_4_3_basic_rules", "Cleaned data with Info mapping set")
        self.rule_builder_sort("A", screenshot_name="rules_example_4_4_sort")

        self.document(
            """
### Building URLs with Regex Replacement

Now for the key step: building the download URLs. We'll use **regex replacement** to transform each accession ID into a complete URL.

- **Pattern**: `.*` (match the entire accession ID)
- **Replacement**: `http://www.uniprot.org/uniprot/\\0.fasta`
  - `\\0` is replaced by the matched text (the accession ID)
  - This constructs the full URL for each protein's FASTA file

This technique works for any repository with predictable URL patterns.
"""
        )
        self.rule_builder_add_regex_replacement(
            "A", ".*", "http://www.uniprot.org/uniprot/\\0.fasta", screenshot_name="rules_example_4_5_url"
        )
        self.screenshot("rules_example_4_6_url_built", "New column C showing the constructed URLs")
        self.document(
            """
### Final Column Mappings

With URLs built, we can now set our final mappings:
- Column A: **List Identifier** (the accession ID)
- Column C: **URL** (the constructed download URL)
- File type: **fasta**
- Collection name: **UP000052092** (the proteome ID)
"""
        )
        self.rule_builder_set_mapping("list-identifiers", "A")
        self.rule_builder_set_mapping("url", "C")
        self.rule_builder_set_extension("fasta")
        self.rule_builder_set_collection_name("UP000052092")
        self.screenshot("rules_example_4_7_mapping_extension_and_name", "Complete configuration ready to upload")

        self.document(
            """
### Viewing Rule Definitions as JSON

The rule builder stores all your transformations as JSON. This is useful for:
- **Reproducibility**: Save and share your exact transformation steps
- **Reuse**: Apply the same rules to new datasets
- **Documentation**: Understanding exactly what transformations were applied

Click the wrench icon to view the JSON representation of these rules.
"""
        )
        rule_builder.view_source.wait_for_and_click()

        self.screenshot("rules_example_4_8_source", "JSON representation of the rule transformations")

        rule_builder.main_button_ok.wait_for_and_click()
        rule_builder.view_source.wait_for_visible()

    def upload_rules_example_5(self, include_result: bool = False):
        """Building matched collections from the same metadata.

        Demonstrates:
        - Creating multiple collections simultaneously
        - Using column splitting to duplicate rows for different file types
        - Reading collection names and datatypes from metadata columns
        - Reusing rules from previous examples (via JSON)
        """
        self.document(
            """
## Building Matched Collections

Sometimes you need to download multiple file types for the same set of samples - for example, both FASTA sequences and GFF3 annotations for the same proteins. This example shows how to create **matched collections** with corresponding list identifiers from a single metadata table.

We'll build two collections:
1. **FASTA files** - protein sequences
2. **GFF3 files** - gene annotations

Both collections will have the same accession IDs as list identifiers, making it easy to process them together in workflows.

The key technique: we'll add columns for BOTH file types, then use **Split Columns** to create two rows per accession - one for FASTA, one for GFF3.
"""
        )
        self.setup_uniprot_example()
        self.wait_for_upload_modal()
        self.screenshot("rules_example_5_1_inputs", "Starting with the same UniProt metadata as Example 4")
        self.upload_rule_build()

        rule_builder = self.components.rule_builder
        rule_builder.view_source.wait_for_and_click()

        self.document(
            """
### Reusing Rules via JSON

Rather than manually recreating the rules from Example 4, we can import the JSON directly. This demonstrates how to reuse transformation logic across datasets.
"""
        )
        with open(RULES_UNIPROT_RULES) as f:
            content = f.read()
        self.rule_builder_enter_source_text(content)
        self.screenshot("rules_example_5_2_source", "Importing rules JSON from Example 4")
        rule_builder.main_button_ok.wait_for_and_click()
        rule_builder.view_source.wait_for_visible()
        self.screenshot("rules_example_5_3_initial_rules", "Rules from Example 4 applied - now we'll extend them")
        self.document(
            """
### Adding Columns for Both File Types

Now we'll add columns to describe both FASTA and GFF3 downloads:
1. Add fixed value "fasta" (datatype for FASTA collection)
2. Add fixed value "UP000052092 FASTA" (collection name)
3. Build GFF3 URLs using regex replacement
4. Add fixed value "gff3" (datatype for GFF3 collection)
5. Add fixed value "UP000052092 GFF3" (collection name)

This creates a wide table where each row has information for both file types.
"""
        )
        self.rule_builder_add_value("fasta", screenshot_name="rules_example_5_4_fasta")
        self.rule_builder_add_value("UP000052092 FASTA")
        self.rule_builder_add_regex_replacement(
            "A", ".*", "http://www.uniprot.org/uniprot/\\0.gff", screenshot_name="rules_example_5_5_url"
        )
        self.rule_builder_add_value("gff3")
        self.rule_builder_add_value("UP000052092 GFF3")
        self.scroll_to_end_of_table()
        self.screenshot("rules_example_5_6_presplit", "Wide table with both FASTA and GFF3 information per row")
        self.document(
            """
### Splitting into Separate Collection Rows

Now we use **Split Columns** to create two rows per accession:
- Odd rows get columns C, D, E (FASTA URL, "fasta" type, "UP000052092 FASTA" name)
- Even rows get columns F, G, H (GFF3 URL, "gff3" type, "UP000052092 GFF3" name)

This converts our wide table into a long table where each row represents one file to download.
"""
        )
        self.rule_builder_split_columns(
            ["C", "D", "E"], ["F", "G", "H"], screenshot_name="rules_example_5_7_split_columns"
        )
        self.screenshot("rules_example_5_8_split", "Data split - now each accession has two rows (FASTA and GFF3)")
        self.document(
            """
### Reading Collection Properties from Metadata

Finally, we set column definitions that read values FROM the metadata:
- Column D: **Type** (file-type read from metadata: "fasta" or "gff3")
- Column E: **Collection Name** (read from metadata: "UP000052092 FASTA" or "UP000052092 GFF3")

This creates two separate collections with matched identifiers.
"""
        )
        self.rule_builder_set_mapping("file-type", "D")
        self.rule_builder_set_mapping("collection-name", "E")
        self.screenshot("rules_example_5_9_mapping", "Mappings configured to create two matched collections")

    def upload_rules_example_6(self, include_result: bool = False):
        """Building nested list collections.

        Demonstrates:
        - Creating nested collection structures (list of lists)
        - Using multiple list identifier columns
        - Extracting grouping information with regex
        - Organizing data by experimental conditions and samples
        """
        self.document(
            """
## Building Nested Lists

For complex experimental designs, you may want **nested collections** - lists within lists. For example:
- Outer level: experimental conditions (treated, untreated, different antibodies, etc.)
- Inner level: individual samples or replicates

This example uses SRA data where samples are organized by library type (e.g., "wtPA14", "con1", "str1", "gen1"). The library names include numbers (con1, con2, etc.) that we need to strip out to group samples by type.

### Key Concept: Multiple List Identifiers

When you assign **two columns** as list identifiers:
- The **first column** becomes the outer (top-level) identifier
- The **second column** becomes the inner (nested) identifier
- Result: a **list:list** collection structure
"""
        )
        self.home()
        self.perform_upload(RULES_EXAMPLE_6_SOURCE)
        self.history_panel_wait_for_hid_ok(1)
        self.upload_rule_start()
        self.upload_rule_set_data_type("Collections")
        self.upload_rule_dataset_dialog()
        self.upload_rule_set_dataset(1)

        self.wait_for_upload_modal()
        self.screenshot("rules_example_6_1_paste", "SRA metadata with library names like 'wtPA14', 'con1', 'str2'")
        self.upload_rule_build()

        rule_builder = self.components.rule_builder
        rule_builder._.wait_for_and_click()

        self.screenshot("rules_example_6_2_rules_landing", "Initial table view - note column J contains URLs")
        self.document(
            """
### Basic Setup

First, the standard operations:
1. Filter the header row
2. Map column J (download_path) to URL
3. Set file type to sra
"""
        )
        self.rule_builder_filter_count(1)

        self.rule_builder_set_mapping("url", "J")
        self.rule_builder_set_extension("sra")
        self.scroll_to_end_of_table()
        self.screenshot("rules_example_6_3_end_of_table", "Scrolled to show library names in column L")
        self.document(
            r"""
### Extracting Group Names with Regex

Column L contains library names like "wtPA14", "con1", "con2", "str1", "gen5". We want to group by the **text prefix** (con, str, gen) but the numbers make each name unique.

We'll use regex to extract just the prefix:
- Pattern: `([^\d]+)\d+`
  - `[^\d]+` = one or more non-digit characters (captures "con", "str", "gen")
  - `\d+` = one or more digits (matches but doesn't capture the numbers)
- This creates a new column with just the group names
"""
        )
        self.rule_builder_add_regex_groups("L", 1, r"([^\d]+)\d+", screenshot_name="rules_example_6_4_regex")
        self.document(
            """
### Setting Multiple List Identifiers

Now we assign **two columns** as list identifiers:
1. Column M (the extracted group: "con", "str", "gen") - becomes the **outer** identifier
2. Column A (the run accession: SRR numbers) - becomes the **inner** identifier

This creates a nested structure where samples are organized by type, with individual runs nested inside each type.
"""
        )
        self.rule_builder_set_mapping(
            "list-identifiers", ["M", "A"], screenshot_name="rules_example_6_5_multiple_identifiers_edit"
        )
        self.scroll_to_end_of_table()
        self.screenshot("rules_example_6_6_multiple_identifiers", "Two list identifier columns configured")
        self.document(
            """
Name the collection and you're ready to create a nested list:list structure, perfect for running tools that need to process samples grouped by experimental condition.
"""
        )
        self.rule_builder_set_collection_name("PRJNA355367")
        self.screenshot("rules_example_6_7_named", "Nested collection configured and ready to upload")

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
