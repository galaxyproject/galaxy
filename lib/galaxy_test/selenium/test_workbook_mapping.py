"""Rule builder mappings inferred from filled-in workbooks.

Galaxy infers the rule builder mapping from the workbook's column headers, so
these tests upload a workbook and assert the mapping it produced rather than
building rules by hand.
"""

from urllib.parse import (
    parse_qs,
    urlparse,
)

from .framework import (
    selenium_test,
    SeleniumTestCase,
)
from .upload_activity_helpers import UsesUploadActivity


class TestWorkbookMapping(SeleniumTestCase, UsesUploadActivity):
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

    def _file_names(self, column_index: int) -> list[str]:
        return [url.rsplit("/", 1)[-1] for url in self.rule_builder_column_values(column_index)]

    def _assert_creating_collections(self) -> None:
        self.components.rule_builder.collection_name_input.wait_for_visible()

    def _assert_example_1_mapping(self) -> None:
        self.components.rule_builder.collection_name_input.assert_absent()
        mapping = self._mapping(3)
        self._assert_mapping(mapping, 0, "name", [0])
        self._assert_mapping(mapping, 1, "url", [1])
        self._assert_mapping(mapping, 2, "dbkey", [2])

    @selenium_test
    def test_dataset_mapping_from_workbook(self):
        """Dataset name, URL and genome columns are recognized by their headers."""
        self.upload_context("rule").upload_workbook(self._workbook(1))
        self._assert_example_1_mapping()

    @selenium_test
    def test_dataset_mapping_from_workbook_full_wizard(self):
        """The same mapping stepped through the wizard instead of the upload shortcut."""
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
        query = parse_qs(urlparse(download_url).query)
        assert query["type"] == ["collection"], download_url
        assert query["collection_type"] == ["list:paired"], download_url

    @selenium_test
    def test_list_collection_mapping_from_workbook(self):
        """URI and TYPE are recognized as alternate spellings of url and file type."""
        self.upload_context("rule").upload_workbook(self._workbook(2))
        self._assert_creating_collections()

        mapping = self._mapping(3)
        self._assert_mapping(mapping, 0, "list_identifiers", [0])
        self._assert_mapping(mapping, 1, "url", [1])
        self._assert_mapping(mapping, 2, "file_type", [2])

    @selenium_test
    def test_list_paired_collection_mapping_from_workbook(self):
        """Two URL columns per row are split into forward and reverse elements."""
        self.upload_context("rule").upload_workbook(self._workbook(3))
        self._assert_creating_collections()

        mapping = self._mapping(4)
        self._assert_mapping(mapping, 0, "list_identifiers", [0])
        self._assert_mapping(mapping, 1, "url", [1])
        self._assert_mapping(mapping, 2, "dbkey", [2])
        self._assert_mapping(mapping, 3, "paired_identifier", [3])

        accessions = ["DRX036147", "DRX036148", "DRX036149"]
        assert self.rule_builder_column_values(0) == [a for a in accessions for _ in range(2)]
        assert self._file_names(1) == [f"{a}_{i}.fastq.gz" for a in accessions for i in "12"]
        assert self.rule_builder_column_values(3) == ["1", "2"] * 3

    @selenium_test
    def test_nested_list_paired_collection_mapping_from_workbook(self):
        """Two identifier columns nest, outermost first, around the split pairs."""
        self.upload_context("rule").upload_workbook(self._workbook(4))
        self._assert_creating_collections()

        mapping = self._mapping(3)
        self._assert_mapping(mapping, 0, "url", [0])
        self._assert_mapping(mapping, 1, "list_identifiers", [1, 2])
        self._assert_mapping(mapping, 2, "paired_identifier", [3])

        runs = ["SRR5680996", "SRR5680997", "SRR5681007", "SRR5681006", "SRR5680998", "SRR5681008"]
        assert self._file_names(0) == [f"{r}_{i}.fastq.gz" for r in runs for i in "12"]
        assert self.rule_builder_column_values(3) == ["1", "2"] * 6
