"""Import datasets and collections from filled-in workbooks.

Galaxy infers the rule builder mapping from the workbook's column headers, so
these tests upload a workbook and assert the mapping it produced rather than
building rules by hand.
"""

from .framework import (
    selenium_test,
    SeleniumTestCase,
)
from .upload_activity_helpers import UsesUploadActivity


class TestWorkbookImport(SeleniumTestCase, UsesUploadActivity):
    ensure_registered = True

    def _workbook(self, index: int) -> str:
        return self.get_filename(f"rules/workbook_example_{index}.tsv")

    def _mapping(self, expected_length: int) -> list:
        rule_json = self.rule_builder_show_and_get_source_as_json()
        assert "mapping" in rule_json, f"No mapping inferred from workbook: {rule_json}"
        mapping = rule_json["mapping"]
        assert len(mapping) == expected_length, f"Expected {expected_length} mappings, got {mapping}"
        return mapping

    def _assert_mapping(self, mapping: list, index: int, expected_type: str, expected_columns: list[int]) -> None:
        entry = mapping[index]
        assert entry["type"] == expected_type, f"Expected mapping {index} to be {expected_type}, got {entry}"
        assert entry["columns"] == expected_columns, f"Expected mapping {index} on {expected_columns}, got {entry}"

    def _assert_example_1_mapping(self) -> None:
        mapping = self._mapping(3)
        self._assert_mapping(mapping, 0, "name", [0])
        self._assert_mapping(mapping, 1, "url", [1])
        self._assert_mapping(mapping, 2, "dbkey", [2])

    @selenium_test
    def test_dataset_import_from_workbook(self):
        """Dataset name, URL and genome columns are recognized by their headers."""
        self.upload_context("rule").upload_workbook(self._workbook(1))
        self._assert_example_1_mapping()

    @selenium_test
    def test_dataset_import_from_workbook_full_wizard(self):
        """The same import stepped through the wizard instead of the upload shortcut."""
        rule_import = self.upload_context("rule").creating("datasets").from_source("workbook")
        assert "type=datasets" in rule_import.workbook_download_url()
        rule_import.upload_workbook_from_card(self._workbook(1))
        self._assert_example_1_mapping()

    @selenium_test
    def test_collection_workbook_template_is_typed(self):
        """Collections pick a collection type first, and the template offered follows it."""
        rule_import = (
            self.upload_context("rule")
            .creating("collections")
            .from_source("workbook")
            .workbook_for_collection_type("list:paired")
        )
        download_url = rule_import.workbook_download_url()
        assert "type=collection" in download_url, download_url
        assert "collection_type=list:paired" in download_url.replace("%3A", ":"), download_url

    @selenium_test
    def test_list_collection_import_from_workbook(self):
        """URI and TYPE are recognized as alternate spellings of url and file type."""
        self.upload_context("rule").upload_workbook(self._workbook(2))

        mapping = self._mapping(3)
        self._assert_mapping(mapping, 0, "list_identifiers", [0])
        self._assert_mapping(mapping, 1, "url", [1])
        self._assert_mapping(mapping, 2, "file_type", [2])

    @selenium_test
    def test_list_paired_collection_import_from_workbook(self):
        """Two URL columns per row are split into forward and reverse elements."""
        self.upload_context("rule").upload_workbook(self._workbook(3))

        mapping = self._mapping(4)
        self._assert_mapping(mapping, 0, "list_identifiers", [0])
        self._assert_mapping(mapping, 1, "url", [1])
        self._assert_mapping(mapping, 2, "dbkey", [2])
        self._assert_mapping(mapping, 3, "paired_identifier", [3])

    @selenium_test
    def test_nested_list_paired_collection_import_from_workbook(self):
        """Two identifier columns nest, outermost first, around the split pairs."""
        self.upload_context("rule").upload_workbook(self._workbook(4))

        mapping = self._mapping(3)
        self._assert_mapping(mapping, 0, "url", [0])
        self._assert_mapping(mapping, 1, "list_identifiers", [1, 2])
        self._assert_mapping(mapping, 2, "paired_identifier", [3])
