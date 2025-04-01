import base64
from io import BytesIO
from typing import (
    Dict,
    List,
    Optional,
)

from openpyxl import (
    load_workbook,
    Workbook,
)
from openpyxl.styles import Font
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet
from pydantic import (
    BaseModel,
    Field,
)
from typing_extensions import Literal

from galaxy.schema.schema import SampleSheetColumnValueT
from .sample_sheet_util import SampleSheetColumnDefinitionsModel

DEFAULT_TITLE = "Sample Sheet for Galaxy"

PrefixRowValuesT = List[List[SampleSheetColumnValueT]]
CreateTitleField = Field(
    DEFAULT_TITLE,
    title="Title of the workbook to generate",
    description="A short title to give the workbook.",
)

ColumnDefinitionsField: SampleSheetColumnDefinitionsModel = Field(
    ...,
    title="Column Descriptions",
    description="A description of the columns expected in the workbook after the first columns described by 'prefix_columns_type'",
)

WorkbookContentField: str = Field(
    ...,
    title="Workbook Content (Base 64 encoded)",
    description="The workbook content (the contents of the xlsx file) that have been base64 encoded.",
)
PrefixRowsField: Optional[PrefixRowValuesT] = Field(
    None,
    title="Prefix sample sheet values",
    description="An area to pre-populate URIs, etc...",
)


class ParsedWorkbook(BaseModel):
    rows: List[Dict[str, SampleSheetColumnValueT]]


class CreateWorkbookFromBase64(BaseModel):
    title: str = CreateTitleField
    prefix_columns_type: Literal["URI"] = "URI"
    column_definitions: str
    prefix_values: Optional[PrefixRowValuesT] = None


class CreateWorkbook(BaseModel):
    title: str = CreateTitleField
    prefix_columns_type: Literal["URI"] = "URI"
    column_definitions: SampleSheetColumnDefinitionsModel = ColumnDefinitionsField
    prefix_values: Optional[PrefixRowValuesT] = None


class ParseWorkbook(BaseModel):
    column_definitions: SampleSheetColumnDefinitionsModel = ColumnDefinitionsField
    content: str = WorkbookContentField


INSTRUCTIONS = [
    "Use this spreadsheet to describe your samples. For each sample (i.e. each file), ensure all the labeled columns are specified and correct.",
    "If you're using Google Sheets, data validation will be applied automatically - just make sure no cell values have a red mark indicating they are invalid.",
    "If you're using Microsft Excel, it is best to run data validation after you've completed filling out this sheet. This can be done by clicking on 'Data' > 'Data Validation' > 'Circle Invalid Data'.",
    "Once data entry is complete, drop this file back into Galaxy to finish creating a sample sheet collection for your inputs.",
]


def parse_workbook(payload: ParseWorkbook) -> ParsedWorkbook:
    decoded_content = base64.b64decode(payload.content)
    file_like = BytesIO(decoded_content)

    workbook = load_workbook(file_like, data_only=True)
    sheet = workbook.active  # Get the first sheet
    rows = []

    column_names = ["URI"] + [c.name for c in payload.column_definitions.root]
    columns_to_read = len(column_names) + 1  # skip the prefix columns...
    for row_index, row in enumerate(sheet.iter_rows(max_col=columns_to_read, values_only=True)):
        if row_index == 0:  # skip column headers
            continue
        if not row[0]:
            break
        parsed_row = {}
        for value, column_name in zip(row, column_names):
            parsed_row[column_name] = value
        rows.append(parsed_row)

    return ParsedWorkbook(
        rows=rows,
    )


# a base64 version of this so we can do short get URLs with real links in the API.
def generate_workbook_from_base64(payload: CreateWorkbookFromBase64) -> Workbook:
    decoded_bytes = base64.b64decode(payload.column_definitions)
    column_definitions = SampleSheetColumnDefinitionsModel.model_validate_json(decoded_bytes)
    create_object = CreateWorkbook(
        title=payload.title,
        prefix_columns_type=payload.prefix_columns_type,
        column_definitions=column_definitions.root,
    )
    return generate_workbook(create_object)


def generate_workbook(payload: CreateWorkbook) -> Workbook:
    # Create a workbook and select the active worksheet
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = payload.title

    column_definitions = payload.column_definitions.root
    num_initial_columns = 1
    headers = [_first_column_header(payload)] + [cd.name for cd in column_definitions]
    worksheet.append(headers)
    _make_bold(worksheet, 1, 0)
    for index in range(len(headers)):
        _make_bold(worksheet, 1, index + 1)

    for index, _ in enumerate(headers):
        if index == 0:
            width = 80
        else:
            width = 20
        _set_width(worksheet, index, width)

    _add_first_column_validation(payload, worksheet)
    worksheet.freeze_panes = "B2"

    for index, column_definition in enumerate(column_definitions):
        validation: Optional[DataValidation] = None
        if column_definition.type == "int":
            validation = DataValidation(type="whole", allow_blank=True)
            # TODO: operator="between", formula1="1", formula2="1000"
        elif column_definition.type == "float":
            validation = DataValidation(type="decimal", allow_blank=True)
            # TODO: operator="between", formula1="1", formula2="1000"
        elif column_definition.type == "boolean":
            column_str = _index_to_excel_column(index + num_initial_columns)
            validation = DataValidation(
                type="custom",
                formula1=f"OR({column_str}2=TRUE, {column_str}2=FALSE)",
                showDropDown=False,
                allow_blank=True,
            )

            dropdown_validation = DataValidation(
                type="list", formula1='"TRUE,FALSE"', showDropDown=False, allow_blank=True
            )
            _add_validation(_index_to_excel_column(index + num_initial_columns), dropdown_validation, worksheet)
        elif column_definition.restrictions:
            list_as_formula = ",".join([str(r) for r in column_definition.restrictions])
            validation = DataValidation(
                type="list", formula1=f'"{list_as_formula}"', showDropDown=False, allow_blank=True
            )
            validation.prompt = "Please select from the list"

        if validation:
            validation.error = "Invalid input"
            validation.errorTitle = "Error"
            validation.promptTitle = column_definition.name
            _add_validation(_index_to_excel_column(index + num_initial_columns), validation, worksheet)

    help_label_index = num_initial_columns + len(column_definitions) + 1
    _set_width(worksheet, help_label_index, 10)

    help_start_row = 3

    worksheet.cell(row=help_start_row, column=help_label_index + 1, value="Instructions")
    bold_font = Font(bold=True)
    worksheet[f"{_index_to_excel_column(help_label_index)}3"].font = bold_font

    for instruction_index, instruction in enumerate(INSTRUCTIONS):
        worksheet.cell(
            row=help_start_row + instruction_index + 1, column=help_label_index + 2, value=f"> {instruction_index + 1}."
        )
        worksheet.cell(row=help_start_row + instruction_index + 1, column=help_label_index + 3, value=instruction)

    column_help_start_row = help_start_row + len(INSTRUCTIONS) + 2

    worksheet.cell(row=column_help_start_row, column=help_label_index + 1, value="Columns")
    _make_bold(worksheet, column_help_start_row, help_label_index)
    # bold_font = Font(bold=True)
    # worksheet[f"{_index_to_excel_column(help_label_index)}{column_help_start_row}"].font = bold_font
    _set_width(worksheet, help_label_index + 1, 15)
    _set_width(worksheet, help_label_index + 2, 150)

    for column_index, column in enumerate(column_definitions):
        worksheet.cell(row=column_help_start_row + column_index + 1, column=help_label_index + 2, value=column.name)
        worksheet.cell(
            row=column_help_start_row + column_index + 1, column=help_label_index + 3, value=column.description
        )

    prefix_rows = payload.prefix_values or []
    prefix_rows_offset = 2  # header + 1-index-ed datastructue
    for row_index, row in enumerate(prefix_rows):
        for column_index, col_value in enumerate(row):
            worksheet.cell(row=row_index + prefix_rows_offset, column=column_index + 1, value=col_value)

    return workbook


def _first_column_header(payload: CreateWorkbook):
    assert payload.prefix_columns_type == "URI"
    return "URI"


def _set_width(worksheet: Worksheet, index: int, width: int):
    worksheet.column_dimensions[_index_to_excel_column(index)].width = width


def _make_bold(worksheet: Worksheet, row: int, column: int):
    bold_font = Font(bold=True)
    worksheet[f"{_index_to_excel_column(column)}{row}"].font = bold_font


def _add_first_column_validation(payload: CreateWorkbook, worksheet: Worksheet):
    assert payload.prefix_columns_type == "URI"
    # Add data validation for "URI" column
    # We cannot assume http/https since drs, gxfiles, etc... are all fine
    uri_validation = DataValidation(type="custom", formula1='=ISNUMBER(FIND("://", E2))', allow_blank=True)
    _add_validation("A", uri_validation, worksheet)


def _add_validation(column: str, data_validation: DataValidation, worksheet: Worksheet):
    worksheet.add_data_validation(data_validation)
    data_validation.add(f"{column}2:{column}1048576")


def _index_to_excel_column(index: int) -> str:
    """Converts a numeric index (0-based) into an Excel column label."""
    if index < 0:
        raise ValueError("Index must be 0 or greater")

    column_label = ""
    while index >= 0:
        column_label = chr(index % 26 + 65) + column_label
        index = index // 26 - 1  # Move to the next "digit" in base-26, adjusting for zero-based indexing

    return column_label
