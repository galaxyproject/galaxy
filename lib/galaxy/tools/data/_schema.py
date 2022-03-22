from typing import (
    Dict,
    List,
)

from pydantic import (
    BaseModel,
    Field,
)


class ToolDataEntry(BaseModel):
    name: str = Field(
        ...,  # Mark this field as required
        title="Name",
        description="The name of this tool data entry",
        example="all_fasta",
    )
    model_class: str = Field(
        ...,  # Mark this field as required
        title="Model class",
        description="The name of class modelling this tool data",
        example="TabularToolDataTable",
    )


class ToolDataEntryList(BaseModel):
    __root__: List[ToolDataEntry] = Field(
        title="A list with details on individual data tables.",
    )


class ToolDataDetails(ToolDataEntry):
    columns: List[str] = Field(
        ...,  # Mark this field as required
        title="Columns",
        description="A list of column names",
        example=["value", "dbkey", "name", "path"],
    )
    # We must use an alias since the name 'fields'
    # shadows a BaseModel attribute
    fields_value: List[List[str]] = Field(
        alias="fields",
        default=[],
        title="Fields",
        description="",  # TODO add documentation
    )


class ToolDataField(BaseModel):
    name: str = Field(
        ...,  # Mark this field as required
        title="Name",
        description="The name of the field",
    )
    model_class: str = Field(
        ...,  # Mark this field as required
        title="Model class",
        description="The name of class modelling this tool data field",
        example="TabularToolDataField",
    )
    # We must use an alias since the name 'fields'
    # shadows a BaseModel attribute
    fields_value: Dict[str, str] = Field(
        ...,  # Mark this field as required
        alias="fields",
        title="Fields",
        description="",  # TODO add documentation
    )
    base_dir: List[str] = Field(
        ...,  # Mark this field as required
        title="Base directories",
        description="A list of directories where the data files are stored",
    )
    files: Dict[str, int] = Field(
        ...,  # Mark this field as required
        title="Files",
        description="A dictionary of file names and their size in bytes",
        example={"file.txt": 136},
    )
    fingerprint: str = Field(
        ...,  # Mark this field as required
        title="Fingerprint",
        description="SHA1 Hash",
        example="22b45237a85c2b3f474bf66888c534387ffe0ced",
    )


class ToolDataItem(BaseModel):
    values: str = Field(
        ...,  # Mark this field as required
        title="Values",
        description=(
            "A `\\t` (TAB) separated list of column __contents__."
            " You must specify a value for each of the columns of the data table."
        ),
        example="value\tdbkey\tname\tpath",
    )
