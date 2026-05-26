"""Base model classes for tool utilities."""

from typing import Optional

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
)
from typing_extensions import Annotated


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


CollectionType = Annotated[Optional[str], AfterValidator(_check_collection_type)]
