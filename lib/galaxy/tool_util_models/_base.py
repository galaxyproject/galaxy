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


def normalize_collection_type_alias(values):
    """Accept legacy ``type:`` as an alias for ``collection_type`` on Collection
    shapes. IWC test authors commonly write ``type: paired`` on nested
    ``class: Collection`` elements; staging code (``load_data_dict`` / fetch
    API) ignores the key, but the strict model previously rejected it.

    Input-only — ``model_dump()`` keeps emitting ``collection_type``. Raises on
    conflicting values rather than picking a winner.
    """
    if not isinstance(values, dict):
        return values
    if "type" not in values:
        return values
    sugar = values.pop("type")
    canonical = values.get("collection_type")
    if canonical is not None and canonical != sugar:
        raise ValueError(
            f"Conflicting collection type: 'collection_type={canonical!r}' vs 'type={sugar!r}' — use collection_type only."
        )
    if canonical is None:
        values["collection_type"] = sugar
    return values
