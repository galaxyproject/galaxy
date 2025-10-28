from galaxy.selenium.stories.data.upload import (
    WORKBOOK_EXAMPLE_1,
    WORKBOOK_EXAMPLE_2,
    WORKBOOK_EXAMPLE_3,
    WORKBOOK_EXAMPLE_4,
)
from .framework import (
    selenium_test,
    SeleniumTestCase,
)

# Screenshot identifiers
SCREENSHOT_EXAMPLE_1_LANDING = "workbook_example_1_landing"
SCREENSHOT_EXAMPLE_1_MAPPED = "workbook_example_1_mapped"
SCREENSHOT_EXAMPLE_2_LANDING = "workbook_example_2_landing"
SCREENSHOT_EXAMPLE_2_CREATE_COLLECTIONS = "workbook_example_2_create_collections"
SCREENSHOT_EXAMPLE_2_MAPPED = "workbook_example_2_mapped"
SCREENSHOT_EXAMPLE_3_LANDING = "workbook_example_3_landing"
SCREENSHOT_EXAMPLE_3_CREATE_COLLECTIONS = "workbook_example_3_create_collections"
SCREENSHOT_EXAMPLE_3_MAPPED = "workbook_example_3_mapped"
SCREENSHOT_EXAMPLE_4_LANDING = "workbook_example_4_landing"
SCREENSHOT_EXAMPLE_4_CREATE_COLLECTIONS = "workbook_example_4_create_collections"
SCREENSHOT_EXAMPLE_4_MAPPED = "workbook_example_4_mapped"

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


class TestWorkbookImport(SeleniumTestCase):
    """Test suite for workbook-based dataset and collection import."""

    ensure_registered = True

    def setup_rules_import(self) -> None:
        """Set up the test environment for rules-based data import.

        Navigates to home and ensures the rules activity is enabled.
        """
        self.home()
        self.document(DOC_ENABLE_RULES_ACTIVITY)
        self.ensure_rules_activity_enabled()

    def _assert_rules_have_mapping(self, rule_json: dict) -> list:
        """Assert that rule JSON contains a mapping and return it.

        Args:
            rule_json: The rule JSON from rule_builder_show_and_get_source_as_json()

        Returns:
            The mapping list from the rule JSON
        """
        assert "mapping" in rule_json
        return rule_json["mapping"]

    def _assert_maps_to_one_column_of_type(
        self, mapping: list, index: int, expected_type: str, expected_column: int
    ) -> None:
        """Assert a mapping entry maps to exactly one column of the expected type.

        Args:
            mapping: The mapping list from rule JSON
            index: Index of the mapping entry to check
            expected_type: Expected mapping type (e.g., "name", "url", "dbkey")
            expected_column: Expected column index (0-based)
        """
        assert mapping[index]["type"] == expected_type
        assert len(mapping[index]["columns"]) == 1
        assert mapping[index]["columns"][0] == expected_column

    @selenium_test
    def test_dataset_import_from_workbook(self):
        """Test importing datasets from a workbook with automatic column mapping.

        This test validates that Galaxy can:
        - Automatically infer column mappings from common header patterns
        - Detect dataset name, URL, and genome (dbkey) columns
        - Correctly map columns without manual rule builder configuration
        """
        self.setup_rules_import()

        self.document(DOC_CLICK_RULES_ACTIVITY)
        self.click_rules_activity()
        self.screenshot(SCREENSHOT_EXAMPLE_1_LANDING, CAPTION_RULES_WIZARD)

        # Document and upload workbook with dataset metadata
        self.document_file(
            WORKBOOK_EXAMPLE_1, "Example workbook with dataset name, URL, and genome columns for simple dataset import"
        )
        self.workbook_upload(WORKBOOK_EXAMPLE_1)

        self.document(DOC_EXAMPLE_1_MAPPED)
        self.screenshot(SCREENSHOT_EXAMPLE_1_MAPPED, CAPTION_EXAMPLE_1_MAPPED)

        # Verify the rule builder mapping
        rule_json = self.rule_builder_show_and_get_source_as_json()
        mapping = self._assert_rules_have_mapping(rule_json)

        self._assert_maps_to_one_column_of_type(mapping, 0, "name", 0)
        self._assert_maps_to_one_column_of_type(mapping, 1, "url", 1)
        self._assert_maps_to_one_column_of_type(mapping, 2, "dbkey", 2)

    @selenium_test
    def test_simple_list_collection_import(self):
        """Test importing a simple list collection from a workbook.

        This test validates that Galaxy can:
        - Detect collection mode when user clicks "collections" button
        - Automatically infer list identifiers and file types
        - Map URL columns for collection elements
        """
        self.setup_rules_import()

        self.document(DOC_CLICK_RULES_ACTIVITY)
        self.click_rules_activity()
        self.screenshot(SCREENSHOT_EXAMPLE_2_LANDING, CAPTION_RULES_WIZARD)

        self.document(DOC_CREATE_COLLECTIONS)
        self.components.rule_builder.create_collections.wait_for_and_click()
        self.screenshot(SCREENSHOT_EXAMPLE_2_CREATE_COLLECTIONS, CAPTION_COLLECTIONS_BUTTON)

        # Document and upload workbook with simple list collection metadata
        self.document_file(
            WORKBOOK_EXAMPLE_2,
            "Example workbook with list identifier, URL, and file type columns for list collection import",
        )
        self.workbook_upload(WORKBOOK_EXAMPLE_2)

        self.document(DOC_EXAMPLE_2_MAPPED)
        self.screenshot(SCREENSHOT_EXAMPLE_2_MAPPED, CAPTION_EXAMPLE_2_MAPPED)

        # Verify the rule builder mapping
        rule_json = self.rule_builder_show_and_get_source_as_json()
        mapping = self._assert_rules_have_mapping(rule_json)

        self._assert_maps_to_one_column_of_type(mapping, 0, "list_identifiers", 0)
        self._assert_maps_to_one_column_of_type(mapping, 1, "url", 1)
        self._assert_maps_to_one_column_of_type(mapping, 2, "file_type", 2)

    @selenium_test
    def test_list_of_pairs_collection_import(self):
        """Test importing a list of pairs collection with automatic pairing.

        This test validates that Galaxy can:
        - Detect paired data from two URL columns per row
        - Automatically split and pair forward/reverse elements
        - Add paired_identifier column for the rule builder
        - Map list identifiers and genome information
        """
        self.setup_rules_import()

        self.document(DOC_CLICK_RULES_ACTIVITY)
        self.click_rules_activity()
        self.screenshot(SCREENSHOT_EXAMPLE_3_LANDING, CAPTION_RULES_WIZARD)

        self.document(DOC_CREATE_COLLECTIONS)
        self.components.rule_builder.create_collections.wait_for_and_click()
        self.screenshot(SCREENSHOT_EXAMPLE_3_CREATE_COLLECTIONS, CAPTION_COLLECTIONS_BUTTON)

        # Document and upload workbook with paired list collection metadata
        self.document_file(
            WORKBOOK_EXAMPLE_3,
            "Example workbook with paired URLs (forward/reverse reads) and genome information for list of pairs import",
        )
        self.workbook_upload(WORKBOOK_EXAMPLE_3)

        self.document(DOC_EXAMPLE_3_MAPPED)
        self.screenshot(SCREENSHOT_EXAMPLE_3_MAPPED, CAPTION_EXAMPLE_3_MAPPED)

        # Verify the rule builder mapping
        rule_json = self.rule_builder_show_and_get_source_as_json()
        mapping = self._assert_rules_have_mapping(rule_json)

        self._assert_maps_to_one_column_of_type(mapping, 0, "list_identifiers", 0)
        self._assert_maps_to_one_column_of_type(mapping, 1, "url", 1)
        self._assert_maps_to_one_column_of_type(mapping, 2, "dbkey", 2)
        self._assert_maps_to_one_column_of_type(mapping, 3, "paired_identifier", 3)

    @selenium_test
    def test_nested_list_of_pairs_import(self):
        """Test importing nested list structures with paired data.

        This test validates that Galaxy can:
        - Handle complex nested list structures
        - Detect and split paired data (two URLs per row)
        - Infer multiple list identifier levels
        - Build correct nested collection hierarchy

        Note: The outer list identifier is always the first one that appears.
        Column order matters for list nesting.
        """
        self.setup_rules_import()

        self.document(DOC_CLICK_RULES_ACTIVITY)
        self.click_rules_activity()
        self.screenshot(SCREENSHOT_EXAMPLE_4_LANDING, CAPTION_RULES_WIZARD)

        self.document(DOC_CREATE_COLLECTIONS)
        self.components.rule_builder.create_collections.wait_for_and_click()
        self.screenshot(SCREENSHOT_EXAMPLE_4_CREATE_COLLECTIONS, CAPTION_COLLECTIONS_BUTTON)

        # Document and upload workbook with nested list of pairs metadata
        self.document_file(
            WORKBOOK_EXAMPLE_4,
            "Example workbook with paired URLs and multiple list identifier columns for nested list of pairs import",
        )
        self.workbook_upload(WORKBOOK_EXAMPLE_4)

        self.document(DOC_EXAMPLE_4_MAPPED)
        self.screenshot(SCREENSHOT_EXAMPLE_4_MAPPED, CAPTION_EXAMPLE_4_MAPPED)
