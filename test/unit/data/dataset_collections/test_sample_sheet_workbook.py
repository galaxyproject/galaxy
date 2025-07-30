import base64
import os
from typing import List

from galaxy.model.dataset_collections.types.sample_sheet_util import (
    SampleSheetColumnDefinitionsModel,
)
from galaxy.model.dataset_collections.types.sample_sheet_workbook import (
    CreateWorkbook,
    CreateWorkbookRequest,
    CreateWorkbookRequestForCollection,
    DatasetCollectionElementLike,
    DatasetCollectionLike,
    DEFAULT_TITLE,
    generate_workbook,
    generate_workbook_from_request,
    generate_workbook_from_request_for_collection,
    parse_workbook,
    parse_workbook_for_collection,
    ParseWorkbook,
    ParseWorkbookForCollection,
)
from galaxy.util.resources import resource_path

WRITE_TEST_WORKBOOKS = False
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


def test_generate_without_seed_data():
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


def test_generate_from_request_without_seed_data():
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


def test_generate_with_seed_data():
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


def test_generate_with_seed_data_paired():
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


class MockDatasetCollectionElement(DatasetCollectionElementLike):

    def __init__(self, id: int, element_identifier: str):
        self.id = id
        self.element_identifier = element_identifier


class MockDatasetCollection(DatasetCollectionLike):
    elements: List[DatasetCollectionElementLike]
    collection_type: str = "list"

    def __init__(self, id: int):
        self.id = id
        self.elements = []


def test_generate_from_collection():
    column_definitions = column_definitions_as_models()
    collection = _mock_collection()
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


def test_parse_base64_workbook():
    content_base64 = unittest_file_to_base64("filled_in_workbook_1.xlsx")
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


def test_parse_base64_workbook_tsv():
    content_base64 = unittest_file_to_base64("filled_in_workbook_1.tsv")
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


def test_parse_base64_workbook_with_dbkey_column():
    content_base64 = unittest_file_to_base64("filled_in_workbook_1_with_dbkey.xlsx")
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


def test_parse_base64_workbook_paired():
    content_base64 = unittest_file_to_base64("filled_in_workbook_paired.xlsx")
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


def test_parse_base64_workbook_paired_or_unpaired():
    content_base64 = unittest_file_to_base64("filled_in_workbook_paired_or_unpaired.xlsx")
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


def column_definitions_as_models():
    return SampleSheetColumnDefinitionsModel.model_validate(TEST_COLUMN_DEFINITIONS_1).root


def test_parse_base64_workbook_from_collection():
    content_base64 = unittest_file_to_base64("filled_in_workbook_from_collection.xlsx")
    collection = _mock_collection()
    parse_payload = ParseWorkbookForCollection(
        column_definitions=column_definitions_as_models(),
        dataset_collection=collection,
        content=content_base64,
    )
    result = parse_workbook_for_collection(parse_payload)
    rows = result.rows
    assert rows


def unittest_file_to_base64(filename: str) -> str:
    path = resource_path("galaxy.model.unittest_utils", filename)
    example_as_bytes = path.read_bytes()
    content_base64 = base64.b64encode(example_as_bytes).decode("utf-8")
    return content_base64


def _mock_collection() -> MockDatasetCollection:
    collection = MockDatasetCollection(23)
    dce = MockDatasetCollectionElement(
        45,
        element_identifier="sample1",
    )
    collection.elements.append(dce)
    return collection
