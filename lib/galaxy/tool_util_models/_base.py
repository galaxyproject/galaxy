"""Base model classes for tool utilities."""

from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
)


class ToolSourceBaseModel(BaseModel):
    pass


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _check_collection_type(v: str) -> str:
    if len(v) == 0:
        raise ValueError("Invalid empty collection_type specified.")
    for level in v.split(":"):
        if level not in ("list", "paired", "paired_or_unpaired", "record", "sample_sheet"):
            raise ValueError(f"Invalid collection_type specified [{v}]")
    return v


CollectionType = Annotated[str | None, AfterValidator(_check_collection_type)]
