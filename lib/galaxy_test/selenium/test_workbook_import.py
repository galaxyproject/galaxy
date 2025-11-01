from galaxy.selenium.stories.data.upload import UploadStoriesMixin
from .framework import (
    selenium_test,
    SeleniumTestCase,
)

DOC_ENABLE_RULES_ACTIVITY = """
If the "Rules-based Data Import" activity is not available in the activity side bar. Click the "... More" activity settings button and enable the option for "Rules-based Data Import".
"""


class TestWorkbookImport(SeleniumTestCase, UploadStoriesMixin):
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
        self.upload_workbook_example_1()
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
        self.upload_workbook_example_2()

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
        self.upload_workbook_example_3()

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
        self.upload_workbook_example_4()

        # Verify the rule builder mapping
        rule_json = self.rule_builder_show_and_get_source_as_json()
        mapping = self._assert_rules_have_mapping(rule_json)

        self._assert_maps_to_one_column_of_type(mapping, 0, "url", 0)
        self._assert_maps_to_one_column_of_type(mapping, 2, "paired_identifier", 3)
