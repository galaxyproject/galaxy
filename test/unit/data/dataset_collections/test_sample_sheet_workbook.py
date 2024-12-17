import base64
import json
import os

from galaxy.model.dataset_collections.types.sample_sheet_workbook import (
    _index_to_excel_column,
    CreateWorkbook,
    CreateWorkbookFromBase64,
    generate_workbook,
    generate_workbook_from_base64,
    parse_workbook,
    ParseWorkbook,
    SampleSheetColumnDefinitionsModel,
)
from galaxy.util.resources import (
    as_file,
    resource_path,
)

WRITE_TEST_WORKBOOKS = False
TEST_DATA = [
    ["https://zenodo.org/records/3263975/files/DRR000770.fastqsanger.gz", 1, "treatment1", False],
    ["https://zenodo.org/records/3263975/files/DRR000771.fastqsanger.gz", 2, "treatment1", False],
    ["https://zenodo.org/records/3263975/files/DRR000772.fastqsanger.gz", 1, "none", True],
    ["https://zenodo.org/records/3263975/files/DRR000773.fastqsanger.gz", 1, "treatment2", False],
    ["https://zenodo.org/records/3263975/files/DRR000774.fastqsanger.gz", 2, "treatment3", False],
    ["https://zenodo.org/records/3263975/files/DRR000775.fastqsanger.gz", "badnumber", "treatment2", False],
    ["https://zenodo.org/records/3263975/files/DRR000776.fastqsanger.gz", 2, "wrongtreament", False],
    ["https://zenodo.org/records/3263975/files/DRR000777.fastqsanger.gz", 3, "treatment2", "badbool"],
]
TEST_COLUMN_DEFINITIONS_1 = [
    {"name": "replicate number", "type": "int", "description": "The replicate number of this sample."},
    {
        "name": "treatment",
        "type": "string",
        "restrictions": ["treatment1", "treatment2", "none"],
        "description": "The treatment code for this sample.",
    },
    {
        "name": "is control?",
        "type": "boolean",
        "description": "Was this sample a control? If TRUE, please ensure treatment is set to none.",
    },
]


def test_generate_without_seed_data():
    create = CreateWorkbook.model_validate({"column_definitions": TEST_COLUMN_DEFINITIONS_1})
    workbook = generate_workbook(create)
    if WRITE_TEST_WORKBOOKS:
        for index, row in enumerate(TEST_DATA):
            for col, column in enumerate(row):
                workbook.active.cell(row=index + 2, column=col + 1, value=column)

        path = "~/test_workbook.xlsx"
        expanded_path = os.path.expanduser(path)
        workbook.save(expanded_path)


def test_generate_base64_without_seed_data():
    json_string = json.dumps(TEST_COLUMN_DEFINITIONS_1)
    column_definition_base64 = base64.b64encode(json_string.encode("utf-8")).decode("utf-8")
    create = CreateWorkbookFromBase64(column_definitions=column_definition_base64)
    workbook = generate_workbook_from_base64(create)
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
            "column_definitions": TEST_COLUMN_DEFINITIONS_1,
            "prefix_values": [
                ["https://zenodo.org/records/3263975/files/DRR000770.fastqsanger.gz"],
                ["https://zenodo.org/records/3263975/files/DRR000771.fastqsanger.gz"],
            ],
        }
    )
    workbook = generate_workbook(create)
    if WRITE_TEST_WORKBOOKS:
        path = "~/test_workbook_seeded.xlsx"
        expanded_path = os.path.expanduser(path)
        workbook.save(expanded_path)


def test_parse_base64_workbook():
    path = resource_path("galaxy.model.unittest_utils", "filled_in_workbook_1.xlsx")
    example_as_bytes = path.read_bytes()
    content_base64 = base64.b64encode(example_as_bytes).decode("utf-8")
    # column_definitions = SampleSheetColumnDefinitionsModel.parse_obj(TEST_COLUMN_DEFINITIONS_1)
    parse_payload = ParseWorkbook(
        column_definitions=TEST_COLUMN_DEFINITIONS_1,
        content=content_base64,
    )
    result = parse_workbook(parse_payload)
    rows = result.rows
    assert rows
    print(result.rows[0])
    assert result.rows[0]["URI"] == "https://zenodo.org/records/3263975/files/DRR000770.fastqsanger.gz"
    assert result.rows[0]["replicate number"] == 1
    assert result.rows[0]["treatment"] == "treatment1"
    assert result.rows[0]["is control?"] == False
    assert result.rows[1]["replicate number"] == 2
    assert result.rows[1]["treatment"] == "treatment1"


def test_index_to_excel_column():
    assert _index_to_excel_column(0) == "A"
    assert _index_to_excel_column(25) == "Z"
    assert _index_to_excel_column(26) == "AA"
    assert _index_to_excel_column(700) == "ZY"
    assert _index_to_excel_column(701) == "ZZ"
    assert _index_to_excel_column(702) == "AAA"
