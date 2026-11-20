"""API models for previewing the outputs of a tool run."""

from typing import (
    Any,
    Literal,
)

from pydantic import Field

from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import Model


class ToolOutputsPreviewRequest(Model):
    """A tool request, in the shape ``POST /api/jobs`` takes, whose outputs to describe."""

    tool_id: str | None = Field(default=None, description="The ID of the tool to run.")
    tool_uuid: str | None = Field(default=None, description="The UUID of the tool to run, for user-defined tools.")
    tool_version: str | None = Field(default=None, description="The version of the tool to run.")
    history_id: DecodedDatabaseIdField | None = Field(
        default=None, description="The history the run would create its outputs in; the current history if not set."
    )
    inputs: dict[str, Any] = Field(default_factory=dict, description="The tool state, as for a tool request.")
    strict: bool = Field(
        default=True,
        description="Turn on strict validation of the inputs that drops support for some inconsistent legacy behavior.",
    )


class ToolOutputPreview(Model):
    name: str = Field(description="The name of the output in the tool.")
    label: str | None = Field(
        description="The name the run gives the created dataset or collection; null if it can't be rendered yet."
    )
    output_type: Literal["data", "collection", "parameter"] = Field(
        description="Whether the run creates a dataset, a collection or a parameter value for this output. "
        "Outputs of a mapped-over run are always collections."
    )
    format: str | None = Field(
        default=None,
        description="The datatype of the created dataset, or of all datasets in the collection; "
        "null if the job decides it or the collection mixes datatypes.",
    )
    format_source: str | None = Field(default=None, description="The input whose datatype this output takes.")
    collection_type: str | None = Field(
        default=None,
        description="The collection type, including the levels added by mapping over inputs, e.g. ``list:paired``.",
    )
    element_count: int | None = Field(
        default=None, description="The number of top-level elements of the collection, if known before the run."
    )
    hidden: bool = Field(default=False, description="Whether the run creates the output hidden.")
    dynamic: bool = Field(default=False, description="Whether the job discovers the datasets of this output.")
    mapped_over: bool = Field(
        default=False, description="Whether the output collects the outputs of the jobs of a mapped-over run."
    )


class ToolOutputsPreview(Model):
    supported: bool = Field(description="Whether the outputs of this tool can be described before it runs.")
    unsupported_reason: str | None = Field(default=None, description="Why the outputs can't be described.")
    job_count: int = Field(default=0, description="The number of jobs the run would create.")
    outputs: list[ToolOutputPreview] = Field(default_factory=list, description="The outputs the run would create.")
