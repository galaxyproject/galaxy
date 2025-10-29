from galaxy.selenium.navigates_galaxy_mixin import NavigatesGalaxyMixin
from ..data import get_example_path


# Convenience constants for workbook examples
WORKBOOK_EXAMPLE_1 = get_example_path("workbook_example_1.tsv")
WORKBOOK_EXAMPLE_2 = get_example_path("workbook_example_2.tsv")
WORKBOOK_EXAMPLE_3 = get_example_path("workbook_example_3.tsv")
WORKBOOK_EXAMPLE_4 = get_example_path("workbook_example_4.tsv")

# Screenshot captions
CAPTION_RULES_WIZARD = "The 'Rules-based Data Import' wizard."
CAPTION_COLLECTIONS_BUTTON = (
    "The collections button will be highlighted after we've clicked it to indicate that we're creating collections."
)
CAPTION_EXAMPLE_1_MAPPED = "Example 1 datasets mapped automatically and properly in the rule builder."
CAPTION_EXAMPLE_2_MAPPED = "Example 2 list mapped automatically and properly in the rule builder."
CAPTION_EXAMPLE_3_MAPPED = (
    "Example 3 - a list of pairs split and paired automatically and properly mapped in the rule builder."
)
CAPTION_EXAMPLE_4_MAPPED = (
    "Example 4 - a nested list of pairs split and paired automatically and properly mapped in the rule builder."
)

# Documentation strings
DOC_ENABLE_RULES_ACTIVITY = """
If the "Rules-based Data Import" activity is not available in the activity side bar. Click the "... More" activity settings button and enable the option for "Rules-based Data Import".
"""

DOC_CLICK_RULES_ACTIVITY = """
Click the  "Rules-based Data Import" activity to begin data import.
"""

DOC_CREATE_COLLECTIONS = "For this example, we start by telling Galaxy we are creating a collection by clicking the large 'collections' button."

DOC_EXAMPLE_1_MAPPED = "Galaxy has correctly inferred the first column named 'name' should be the uploaded dataset names, the second column named 'url' is the URL of the datasets to upload, and the third column named 'genome' is the Galaxy genome (also known as build or dbkey) to use for the uploaded datasets."

DOC_EXAMPLE_2_MAPPED = "Galaxy has correctly inferred the first column is a list identifier, the second column named 'URI' is the URL of the datasets to upload, and the third column named 'type' is the Galaxy type for the uploaded datasets."

DOC_EXAMPLE_3_MAPPED = "Galaxy has correctly inferred the second and third columns are paired data (since there are two URLs per row) and has split the data before feeding it to the rule builder. Galaxy has also inferred the first column should be the list identifier and the third column named 'build' is the Galaxy genome (also sometimes called dbkey). The Galaxy rule builder expects paired data to contain a column specifying the first and second elements of the pair - this column has been added and can be seen in column 4."

DOC_EXAMPLE_4_MAPPED = "Galaxy has correctly inferred the first and second columns are paired data (since there are two URLs per row) and has split the data before feeding it to the rule builder. Galaxy has also inferred the third and fourth column are list identifiers and has built up a nested list structure. Be careful here though - the outer list identifier is always the first one that appears - the column headers for columns 3 and 4 had been 'Inner List Identifier' and 'Outer List Identifier' in that order the mapping would be unchanged and these list identifiers would be inverted relative to what would be intended from these column names."


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
        self.document(DOC_CLICK_RULES_ACTIVITY)
        self.click_rules_activity()
        self.screenshot("workbook_example_1_landing", CAPTION_RULES_WIZARD)

        # Document and upload workbook with dataset metadata
        self.document_file(
            WORKBOOK_EXAMPLE_1, "Example workbook with dataset name, URL, and genome columns for simple dataset import"
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
        self.document(DOC_CLICK_RULES_ACTIVITY)
        self.click_rules_activity()
        self.screenshot("workbook_example_2_landing", CAPTION_RULES_WIZARD)

        self.document(DOC_CREATE_COLLECTIONS)
        self.components.rule_builder.create_collections.wait_for_and_click()
        self.screenshot("workbook_example_2_create_collections", CAPTION_COLLECTIONS_BUTTON)

        # Document and upload workbook with simple list collection metadata
        self.document_file(
            WORKBOOK_EXAMPLE_2,
            "Example workbook with list identifier, URL, and file type columns for list collection import",
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
        self.document(DOC_CLICK_RULES_ACTIVITY)
        self.click_rules_activity()
        self.screenshot("workbook_example_3_landing", CAPTION_RULES_WIZARD)

        self.document(DOC_CREATE_COLLECTIONS)
        self.components.rule_builder.create_collections.wait_for_and_click()
        self.screenshot("workbook_example_3_create_collections", CAPTION_COLLECTIONS_BUTTON)

        # Document and upload workbook with paired list collection metadata
        self.document_file(
            WORKBOOK_EXAMPLE_3,
            "Example workbook with paired URLs (forward/reverse reads) and genome information for list of pairs import",
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
        self.document(DOC_CLICK_RULES_ACTIVITY)
        self.click_rules_activity()
        self.screenshot("workbook_example_4_landing", CAPTION_RULES_WIZARD)

        self.document(DOC_CREATE_COLLECTIONS)
        self.components.rule_builder.create_collections.wait_for_and_click()
        self.screenshot("workbook_example_4_create_collections", CAPTION_COLLECTIONS_BUTTON)

        # Document and upload workbook with nested list of pairs metadata
        self.document_file(
            WORKBOOK_EXAMPLE_4,
            "Example workbook with paired URLs and multiple list identifier columns for nested list of pairs import",
        )
        self.workbook_upload(WORKBOOK_EXAMPLE_4)

        self.document(DOC_EXAMPLE_4_MAPPED)
        self.screenshot("workbook_example_4_mapped", CAPTION_EXAMPLE_4_MAPPED)
