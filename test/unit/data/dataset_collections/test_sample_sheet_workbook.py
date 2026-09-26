import base64
import os

import pytest

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model import (
    DatasetCollection,
    DatasetCollectionElement,
)
from galaxy.model.dataset_collections.types.sample_sheet_util import (
    SampleSheetColumnDefinitionsModel,
)
from galaxy.model.dataset_collections.types.sample_sheet_workbook import (
    _list_to_sample_sheet_collection_type,
    CreateWorkbook,
    CreateWorkbookRequest,
    CreateWorkbookRequestForCollection,
    DEFAULT_TITLE,
    generate_workbook,
    generate_workbook_from_request,
    generate_workbook_from_request_for_collection,
    parse_workbook,
    parse_workbook_for_collection,
    ParseWorkbook,
    ParseWorkbookForCollection,
    SAMPLE_SHEET_COLLECTION_TYPES,
)
from galaxy.util.resources import resource_path

# Test configuration
WRITE_TEST_WORKBOOKS = False

# Test data
TEST_DATA = [
    ["https://zenodo.org/records/3263975/files/DRR000770.fastqsanger.gz", "DRR000770", 1, "treatment1", False],
    ["https://zenodo.org/records/3263975/files/DRR000771.fastqsanger.gz", "DRR000771", 2, "treatment1", False],
    ["https://zenodo.org/records/3263975/files/DRR000772.fastqsanger.gz", "DRR000772", 1, "none", True],
    ["https://zenodo.org/records/3263975/files/DRR000773.fastqsanger.gz", "DRR000773", 1, "treatment2", False],
    ["https://zenodo.org/records/3263975/files/DRR000774.fastqsanger.gz", "DRR000774", 2, "treatment3", False],
    [
        "https://zenodo.org/records/3263975/files/DRR000775.fastqsanger.gz",
        "DRR000775",
        "badnumber",
        "treatment2",
        False,
    ],
    ["https://zenodo.org/records/3263975/files/DRR000776.fastqsanger.gz", "DRR000776", 2, "wrongtreament", False],
    ["https://zenodo.org/records/3263975/files/DRR000777.fastqsanger.gz", "DRR000777", 3, "treatment2", "badbool"],
]
TEST_COLUMN_DEFINITIONS_1 = [
    {
        "name": "replicate number",
        "type": "int",
        "description": "The replicate number of this sample.",
        "default_value": 0,
        "optional": False,
    },
    {
        "name": "treatment",
        "type": "string",
        "restrictions": ["treatment1", "treatment2", "none"],
        "description": "The treatment code for this sample.",
        "default_value": "none",
        "optional": False,
    },
    {
        "name": "is control?",
        "type": "boolean",
        "description": "Was this sample a control? If TRUE, please ensure treatment is set to none.",
        "default_value": True,
        "optional": False,
    },
]


# Helper functions
def _make_collection(collection_type: str, element_identifiers: list[str]) -> DatasetCollection:
    """Create a real DatasetCollection with DatasetCollectionElements."""
    collection = DatasetCollection(collection_type=collection_type)
    for i, identifier in enumerate(element_identifiers):
        DatasetCollectionElement(
            id=i + 1,
            collection=collection,
            element=DatasetCollectionElement.UNINITIALIZED_ELEMENT,
            element_index=i,
            element_identifier=identifier,
        )
    return collection


def _column_definitions_as_models():
    return SampleSheetColumnDefinitionsModel.model_validate(TEST_COLUMN_DEFINITIONS_1).root


def _unittest_file_to_base64(filename: str) -> str:
    path = resource_path("galaxy.model.unittest_utils", filename)
    example_as_bytes = path.read_bytes()
    content_base64 = base64.b64encode(example_as_bytes).decode("utf-8")
    return content_base64


class TestWorkbookGeneration:
    """Tests for workbook generation functions."""

    def test_generate_without_seed_data(self):
        create = CreateWorkbook.model_validate(
            {"collection_type": "sample_sheet", "column_definitions": TEST_COLUMN_DEFINITIONS_1}
        )
        workbook = generate_workbook(create)
        if WRITE_TEST_WORKBOOKS:
            for index, row in enumerate(TEST_DATA):
                for col, column in enumerate(row):
                    workbook.active.cell(row=index + 2, column=col + 1, value=column)

            path = "~/test_workbook.xlsx"
            expanded_path = os.path.expanduser(path)
            workbook.save(expanded_path)

    def test_generate_from_request_without_seed_data(self):
        column_definition = TEST_COLUMN_DEFINITIONS_1
        create = CreateWorkbookRequest(collection_type="sample_sheet", column_definitions=column_definition)
        workbook = generate_workbook_from_request(create)
        if WRITE_TEST_WORKBOOKS:
            for index, row in enumerate(TEST_DATA):
                for col, column in enumerate(row):
                    workbook.active.cell(row=index + 2, column=col + 1, value=column)

            path = "~/test_workbook_from_base64.xlsx"
            expanded_path = os.path.expanduser(path)
            workbook.save(expanded_path)

    def test_generate_with_seed_data(self):
        create = CreateWorkbook.model_validate(
            {
                "collection_type": "sample_sheet",
                "column_definitions": TEST_COLUMN_DEFINITIONS_1,
                "prefix_values": [
                    ["https://zenodo.org/records/3263975/files/DRR000770.fastqsanger.gz", "DRR000770"],
                    ["https://zenodo.org/records/3263975/files/DRR000771.fastqsanger.gz", "DRR000770"],
                ],
            }
        )
        workbook = generate_workbook(create)
        if WRITE_TEST_WORKBOOKS:
            path = "~/test_workbook_seeded.xlsx"
            expanded_path = os.path.expanduser(path)
            workbook.save(expanded_path)

    def test_generate_with_seed_data_paired(self):
        create = CreateWorkbook.model_validate(
            {
                "collection_type": "sample_sheet:paired",
                "column_definitions": TEST_COLUMN_DEFINITIONS_1,
                "prefix_values": [
                    [
                        "https://zenodo.org/record/3554549/files/SRR1799908_forward.fastq",
                        "https://zenodo.org/record/3554549/files/SRR1799908_reverse.fastq",
                        "SRR1799908",
                    ],
                ],
            }
        )
        workbook = generate_workbook(create)
        if WRITE_TEST_WORKBOOKS:
            path = "~/test_workbook_seeded_paired.xlsx"
            expanded_path = os.path.expanduser(path)
            workbook.save(expanded_path)

    def test_generate_from_list_collection(self):
        column_definitions = _column_definitions_as_models()
        collection = _make_collection("list", ["sample1"])
        create = CreateWorkbookRequestForCollection(
            title=DEFAULT_TITLE,
            dataset_collection=collection,
            column_definitions=column_definitions,
        )
        workbook = generate_workbook_from_request_for_collection(create)
        if WRITE_TEST_WORKBOOKS:
            path = "~/test_workbook_seeded_from_collection.xlsx"
            expanded_path = os.path.expanduser(path)
            workbook.save(expanded_path)

    def test_generate_from_sample_sheet_collection(self):
        """Test generating workbook from existing sample_sheet collection (issue #21542)."""
        column_definitions = _column_definitions_as_models()
        collection = _make_collection("sample_sheet", ["sample1", "sample2"])
        create = CreateWorkbookRequestForCollection(
            title=DEFAULT_TITLE,
            dataset_collection=collection,
            column_definitions=column_definitions,
        )
        workbook = generate_workbook_from_request_for_collection(create)
        sheet = workbook.active
        assert sheet.title == DEFAULT_TITLE
        assert sheet["A1"].value == "Element Identifier"
        assert sheet["A2"].value == "sample1"
        assert sheet["A3"].value == "sample2"
        assert sheet["A4"].value is None

    def test_generate_from_sample_sheet_paired_collection(self):
        """Test generating workbook from existing sample_sheet:paired collection (issue #21542)."""
        column_definitions = _column_definitions_as_models()
        collection = _make_collection("sample_sheet:paired", ["paired_sample1"])
        create = CreateWorkbookRequestForCollection(
            title=DEFAULT_TITLE,
            dataset_collection=collection,
            column_definitions=column_definitions,
        )
        workbook = generate_workbook_from_request_for_collection(create)
        sheet = workbook.active
        assert sheet.title == DEFAULT_TITLE
        assert sheet["A1"].value == "Element Identifier"
        assert sheet["A2"].value == "paired_sample1"
        assert sheet["A3"].value is None


class TestWorkbookParsing:
    """Tests for workbook parsing functions."""

    def test_parse_xlsx(self):
        content_base64 = _unittest_file_to_base64("filled_in_workbook_1.xlsx")
        parse_payload = ParseWorkbook(
            collection_type="sample_sheet",
            column_definitions=TEST_COLUMN_DEFINITIONS_1,
            content=content_base64,
        )
        result = parse_workbook(parse_payload)
        rows = result.rows
        assert rows
        first_row = result.rows[0]
        assert first_row["url"] == "https://zenodo.org/records/3263975/files/DRR000770.fastqsanger.gz"
        assert first_row["replicate number"] == 1
        assert first_row["treatment"] == "treatment1"
        assert first_row["is control?"] is False
        second_row = result.rows[1]
        assert second_row["replicate number"] == 2
        assert second_row["treatment"] == "treatment1"

    def test_parse_tsv(self):
        content_base64 = _unittest_file_to_base64("filled_in_workbook_1.tsv")
        parse_payload = ParseWorkbook(
            collection_type="sample_sheet",
            column_definitions=TEST_COLUMN_DEFINITIONS_1,
            content=content_base64,
        )
        result = parse_workbook(parse_payload)
        rows = result.rows
        assert rows
        first_row = result.rows[0]
        assert first_row["url"] == "https://zenodo.org/records/3263975/files/DRR000770.fastqsanger.gz"
        assert first_row["replicate number"] == 1
        assert first_row["treatment"] == "treatment1"
        assert first_row["is control?"] is False
        second_row = result.rows[1]
        assert second_row["replicate number"] == 2
        assert second_row["treatment"] == "treatment1"

    def test_parse_with_dbkey_column(self):
        content_base64 = _unittest_file_to_base64("filled_in_workbook_1_with_dbkey.xlsx")
        parse_payload = ParseWorkbook(
            collection_type="sample_sheet",
            column_definitions=TEST_COLUMN_DEFINITIONS_1,
            content=content_base64,
        )
        result = parse_workbook(parse_payload)
        rows = result.rows
        assert rows
        first_row = result.rows[0]
        assert first_row["url"] == "https://zenodo.org/records/3263975/files/DRR000770.fastqsanger.gz"
        assert first_row["replicate number"] == 1
        assert first_row["treatment"] == "treatment1"
        assert first_row["is control?"] is False
        assert result.extra_columns[0].type == "dbkey"
        assert first_row["dbkey"] == "hg18"

    def test_parse_paired(self):
        content_base64 = _unittest_file_to_base64("filled_in_workbook_paired.xlsx")
        parse_payload = ParseWorkbook(
            collection_type="sample_sheet:paired",
            column_definitions=TEST_COLUMN_DEFINITIONS_1,
            content=content_base64,
        )
        result = parse_workbook(parse_payload)
        rows = result.rows
        assert rows
        assert result.rows[0]["url"] == "https://zenodo.org/record/3554549/files/SRR1799908_forward.fastq"
        assert result.rows[0]["url_1"] == "https://zenodo.org/record/3554549/files/SRR1799908_reverse.fastq"
        assert result.rows[0]["replicate number"] == 1
        assert result.rows[0]["treatment"] == "treatment1"
        assert result.rows[0]["is control?"] is False

    def test_parse_paired_or_unpaired(self):
        content_base64 = _unittest_file_to_base64("filled_in_workbook_paired_or_unpaired.xlsx")
        parse_payload = ParseWorkbook(
            collection_type="sample_sheet:paired_or_unpaired",
            column_definitions=TEST_COLUMN_DEFINITIONS_1,
            content=content_base64,
        )
        result = parse_workbook(parse_payload)
        rows = result.rows
        assert rows
        assert result.rows[0]["url"] == "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed"
        assert result.rows[0]["url_1"] is None
        assert result.rows[0]["replicate number"] == 1
        assert result.rows[0]["treatment"] == "treatment1"
        assert result.rows[0]["is control?"] is False

        assert result.rows[1]["url"] == "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed"
        assert result.rows[1]["url_1"] == "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed"
        assert result.rows[1]["replicate number"] == 2
        assert result.rows[1]["treatment"] == "treatment2"
        assert result.rows[1]["is control?"] is True

    def test_parse_from_collection(self):
        content_base64 = _unittest_file_to_base64("filled_in_workbook_from_collection.xlsx")
        collection = _make_collection("list", ["sample1"])
        parse_payload = ParseWorkbookForCollection(
            column_definitions=_column_definitions_as_models(),
            dataset_collection=collection,
            content=content_base64,
        )
        result = parse_workbook_for_collection(parse_payload)
        rows = result.rows
        assert rows


class TestListToSampleSheetCollectionType:
    """Tests for _list_to_sample_sheet_collection_type() function."""

    def test_converts_list_types(self):
        """Test conversion of list types to sample_sheet types."""
        assert _list_to_sample_sheet_collection_type("list") == "sample_sheet"
        assert _list_to_sample_sheet_collection_type("list:paired") == "sample_sheet:paired"
        assert _list_to_sample_sheet_collection_type("list:paired_or_unpaired") == "sample_sheet:paired_or_unpaired"

    def test_passthrough_sample_sheet_types(self):
        """Test that sample_sheet types pass through unchanged (issue #21542 fix)."""
        assert _list_to_sample_sheet_collection_type("sample_sheet") == "sample_sheet"
        assert _list_to_sample_sheet_collection_type("sample_sheet:paired") == "sample_sheet:paired"
        assert (
            _list_to_sample_sheet_collection_type("sample_sheet:paired_or_unpaired")
            == "sample_sheet:paired_or_unpaired"
        )
        assert _list_to_sample_sheet_collection_type("sample_sheet:record") == "sample_sheet:record"

    def test_all_sample_sheet_types_passthrough(self):
        """Test all types in SAMPLE_SHEET_COLLECTION_TYPES pass through."""
        for collection_type in SAMPLE_SHEET_COLLECTION_TYPES:
            result = _list_to_sample_sheet_collection_type(collection_type)
            assert result == collection_type

    def test_invalid_type_raises_exception(self):
        """Test that invalid types raise RequestParameterInvalidException."""
        with pytest.raises(RequestParameterInvalidException):
            _list_to_sample_sheet_collection_type("invalid_type")

        with pytest.raises(RequestParameterInvalidException):
            _list_to_sample_sheet_collection_type("paired")

        with pytest.raises(RequestParameterInvalidException):
            _list_to_sample_sheet_collection_type("")

    def test_list_record_raises_not_implemented(self):
        """Test that list:record raises NotImplementedError (WIP)."""
        with pytest.raises(NotImplementedError):
            _list_to_sample_sheet_collection_type("list:record")
