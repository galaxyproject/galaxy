from typing import (
    Any,
    Optional,
)

from pydantic import Field

from galaxy.schema.schema import Model


class GetToolPredictionsPayload(Model):
    tool_sequence: Optional[Any] = Field(
        None,
        title="Tool Sequence",
        description="comma separated sequence of tool ids",
    )
    remote_model_url: Optional[Any] = Field(
        None,
        title="Remote Model URL",
        description="Path to the deep learning model",
    )


class ToolPredictionsSummary(Model):
    current_tool: Optional[Any] = Field(
        None,
        title="Current Tools",
        description="A comma separated sequence of the current tool ids",
    )
    predicted_data: Optional[Any] = Field(
        None,
        title="Recommended Tools",
        description="List of predictions",
    )
