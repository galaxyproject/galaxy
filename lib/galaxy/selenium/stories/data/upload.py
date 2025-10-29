from galaxy.selenium.navigates_galaxy_mixin import NavigatesGalaxyMixin
from ..data import get_example_path


# Convenience constants for workbook examples
WORKBOOK_EXAMPLE_1 = get_example_path("workbook_example_1.tsv")
WORKBOOK_EXAMPLE_2 = get_example_path("workbook_example_2.tsv")
WORKBOOK_EXAMPLE_3 = get_example_path("workbook_example_3.tsv")
WORKBOOK_EXAMPLE_4 = get_example_path("workbook_example_4.tsv")

# Screenshot captions
CAPTION_RULES_WIZARD = "The Rules-based Data Import wizard interface"
CAPTION_COLLECTIONS_BUTTON = (
    "The collections button highlighted to indicate collection mode is active"
)
CAPTION_EXAMPLE_1_MAPPED = "The rule builder showing automatically detected column mappings for name, URL, and genome"
CAPTION_EXAMPLE_2_MAPPED = "The rule builder showing automatically detected list identifier, URI, and type column mappings"
CAPTION_EXAMPLE_3_MAPPED = (
    "The rule builder showing automatic paired data detection - notice the data has been split with forward/reverse identifiers added"
)
CAPTION_EXAMPLE_4_MAPPED = (
    "The rule builder showing automatic nested structure detection from multiple list identifier columns and paired URL columns"
)

# Documentation strings
DOC_ENABLE_RULES_ACTIVITY = """
If the "Rules-based Data Import" activity is not available in the activity side bar, click the "... More" activity settings button and enable the option for "Rules-based Data Import".
"""

DOC_CLICK_RULES_ACTIVITY = """
Click the "Rules-based Data Import" activity to begin data import.
"""

DOC_CREATE_COLLECTIONS = """
For this example, we'll create a collection rather than individual datasets. Click the large 'collections' button to indicate that we want to build a collection. The button will remain highlighted to show that collection mode is active.
"""

DOC_EXAMPLE_1_INTRO = """
## Example 1: Uploading Simple Datasets with Automatic Metadata Detection

In this first example, we'll upload a set of FASTQ sequencing files from a spreadsheet. Galaxy's auto-detection feature will automatically recognize the column headers and map them to the appropriate metadata fields without any manual configuration.

This is the easiest way to upload multiple datasets when your spreadsheet has clear, recognizable column names.
"""

DOC_EXAMPLE_1_MAPPED = """
Galaxy has automatically detected the column mappings based on the header names:
- The **name** column is recognized as the dataset name
- The **url** column is identified as the download URL for each file
- The **genome** column is mapped to the reference genome (also called build or dbkey)

Notice that we didn't have to configure any rules manually - Galaxy recognized these standard column patterns and set up the import automatically. This is perfect for straightforward data uploads where you have clear metadata in your spreadsheet.
"""

DOC_EXAMPLE_2_INTRO = """
## Example 2: Creating a Simple List Collection

Building on the previous example, we'll now create a **list collection** - a way to group related datasets together. Collections are useful when you want to run the same analysis on multiple samples at once.

The key difference here is that our spreadsheet includes a **LIST IDENTIFIER** column, which tells Galaxy how to name each element in the collection.
"""

DOC_EXAMPLE_2_MAPPED = """
Galaxy has recognized the column structure for a list collection:
- The **LIST IDENTIFIER** column is detected as the collection element identifiers
- The **URI** column (another common name for URLs) is mapped to the download locations
- The **TYPE** column specifies the file type (datatype) for each dataset

Even though these column names are different from Example 1 (URI instead of url, TYPE instead of format), Galaxy's auto-detection is flexible enough to recognize these alternative naming patterns. This means your spreadsheets don't need to follow one rigid format.
"""

DOC_EXAMPLE_3_INTRO = """
## Example 3: Paired-End Sequencing Data

Many sequencing experiments produce **paired-end reads** - two files per sample (forward and reverse reads). Galaxy can automatically detect this structure when your spreadsheet has two URL columns per row.

This example demonstrates how Galaxy splits the paired data and creates a **list of pairs collection** - the appropriate structure for paired-end sequencing data.
"""

DOC_EXAMPLE_3_MAPPED = """
Galaxy has automatically detected and processed the paired data structure:
- The **forward_url** and **reverse_url** columns are recognized as paired data (two URLs per sample)
- Galaxy automatically **split the data** - notice that each row in the spreadsheet becomes two rows in the rule builder
- A new **paired identifier** column (column 4) has been added automatically, marking which reads are "forward" and "reverse"
- The **list identifier** column defines the sample names
- The **genome** column provides the reference build for each sample

This automatic splitting and pairing is one of the most powerful features of the rule-based uploader - it handles the complexity of paired data without requiring manual rule configuration.
"""

DOC_EXAMPLE_4_INTRO = """
## Example 4: Nested Collections with Paired Data

For complex experiments, you might need **nested collections** - collections within collections. A common example is organizing paired-end data by experimental condition (e.g., different ChIP-seq targets) with technical replicates.

This example shows how Galaxy automatically builds nested structures when your spreadsheet has multiple identifier columns. **The key concept**: column order determines the nesting hierarchy.
"""

DOC_EXAMPLE_4_MAPPED = """
Galaxy has detected a complex nested structure from the spreadsheet:
- The **URI 1** and **URI 2** columns are recognized as paired data and automatically split
- The **Outer List Identifier** and **Inner List Identifier** columns create a nested list structure
- The result is a **list of lists of pairs** collection - perfect for organizing paired-end data by experimental groups

**Important**: Column order determines the nesting hierarchy. The **third column** (labeled "Outer List Identifier") becomes the outer level, and the **fourth column** (labeled "Inner List Identifier") becomes the inner level. This is based purely on column position, not the column names.

If we had swapped the order of these columns in the spreadsheet (putting "Inner List Identifier" in column 3), that column would actually become the outer level - the labels in the headers don't affect the structure, only the column order matters.

This example demonstrates the most advanced capability of auto-detection, handling complex hierarchical data structures that are common in large sequencing studies.
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
        self.document(DOC_EXAMPLE_1_INTRO)
        self.document(DOC_CLICK_RULES_ACTIVITY)
        self.click_rules_activity()
        self.screenshot("workbook_example_1_landing", CAPTION_RULES_WIZARD)

        self.document_file(
            WORKBOOK_EXAMPLE_1, "Example workbook with dataset name, URL, and genome columns"
        )
        self.workbook_upload(WORKBOOK_EXAMPLE_1)

        self.document(DOC_EXAMPLE_1_MAPPED)
        self.screenshot("workbook_example_1_mapped", CAPTION_EXAMPLE_1_MAPPED)

    def upload_workbook_example_2(self):
        """Importing a simple list collection from a workbook.

        Demonstrates that Galaxy can:
        - Detect collection mode when user clicks "collections" button
        - Automatically infer list identifiers and file types
        - Map URL columns for collection elements
        """
        self.home()
        self.document(DOC_EXAMPLE_2_INTRO)
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

        self.document(DOC_EXAMPLE_2_MAPPED)
        self.screenshot("workbook_example_2_mapped", CAPTION_EXAMPLE_2_MAPPED)

    def upload_workbook_example_3(self):
        """Importing a list of pairs collection with automatic pairing.

        This test validates that Galaxy can:
        - Detect paired data from two URL columns per row
        - Automatically split and pair forward/reverse elements
        - Add paired_identifier column for the rule builder
        - Map list identifiers and genome information
        """
        self.home()
        self.document(DOC_EXAMPLE_3_INTRO)
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

        self.document(DOC_EXAMPLE_3_MAPPED)
        self.screenshot("workbook_example_3_mapped", CAPTION_EXAMPLE_3_MAPPED)

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
        self.document(DOC_EXAMPLE_4_INTRO)
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

        self.document(DOC_EXAMPLE_4_MAPPED)
        self.screenshot("workbook_example_4_mapped", CAPTION_EXAMPLE_4_MAPPED)
