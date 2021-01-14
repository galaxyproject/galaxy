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
        description="The name of this composite file",
        example="all_fasta"
    )
    model_class: str = Field(
        ...,  # Mark this field as required
        title="Model class",
        description="The name of this composite file",
        example="TabularToolDataTable"
    )


class ToolDataEntryList(BaseModel):
    __root__: List[ToolDataEntry] = Field(
        default=[],
        title="A list with details on individual data tables.",
    )
