from typing import (
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
        example="all_fasta"
    )
    model_class: str = Field(
        ...,  # Mark this field as required
        title="Model class",
        description="The name of class modelling this tool data",
        example="TabularToolDataTable"
    )


class ToolDataEntryList(BaseModel):
    __root__: List[ToolDataEntry] = Field(
        default=[],
        title="A list with details on individual data tables.",
    )


class ToolDataDetails(ToolDataEntry):
    columns: List[str] = Field(
        ...,  # Mark this field as required
        title="Columns",
        description="A list of column names",
        example=[
            "value",
            "dbkey",
            "name",
            "path"
        ]
    )
    # We must use an alias since the name 'fields'
    # shadows a BaseModel attribute
    fields_td: List[List[str]] = Field(
        alias='fields',
        default=[],
        title="Fields",
        description="",  # TODO add documentation
        example="all_fasta"
    )
