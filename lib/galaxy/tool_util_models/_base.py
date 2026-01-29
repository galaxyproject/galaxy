"""Base model classes for tool utilities."""

from pydantic import (
    BaseModel,
    ConfigDict,
)


class ToolSourceBaseModel(BaseModel):
    model_config = ConfigDict(field_title_generator=lambda field_name, field_info: field_name.lower())
