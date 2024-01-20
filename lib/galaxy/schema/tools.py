import json
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from pydantic import (
    ConfigDict,
    Field,
    field_validator,
)

from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import Model


class CreateToolPayload(Model):
    # def __init__(self, **data):
    #     self.model_config = ConfigDict(extra="allow")
    #     # Dynamically add fields based on keys starting with 'files_' or '__files_'
    #     for key, value in data.items():
    #         if key.startswith("files_") or key.startswith("__files_"):
    #             setattr(
    #                 self, key, Field(default=value, title=key, description="Files related to the creation of the tool.")
    #             )
    #     super().__init__(**data)

    tool_id: Optional[Any] = Field(
        default=None,
        title="Tool ID",
        description="The ID of the tool to execute.",
    )
    tool_uuid: Optional[Any] = Field(
        default=None,
        title="Tool UUID",
        description="The UUID of the tool to execute.",
    )
    action: Optional[str] = Field(
        default=None,
        title="Action",
        description="The action to perform",
    )
    tool_version: Optional[str] = Field(
        default=None,
        title="Tool Version",
        description="The version of the tool",
    )
    history_id: Optional[DecodedDatabaseIdField] = Field(
        default=None,
        title="History ID",
        description="The ID of the history",
    )

    @field_validator("inputs", mode="before", check_fields=False)
    @classmethod
    def inputs_string_to_json(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    inputs: Dict[str, Any] = Field(
        default={},
        title="Inputs",
        description="The input data",
    )
    use_cached_job: Optional[bool] = Field(
        default=False,
        title="Use Cached Job",
        description="Flag indicating whether to use a cached job",
    )
    preferred_object_store_id: Optional[str] = Field(
        default=None,
        title="Preferred Object Store ID",
        description="The ID of the preferred object store",
    )
    input_format: Optional[str] = Field(
        default="legacy",
        title="Input Format",
        description="The format of the input",
    )
    data_manager_mode: Optional[str] = Field(
        default=None,
        title="Data Manager Mode",
        description="The mode of the data manager",
    )
    send_email_notification: Optional[bool] = Field(
        default=None,
        title="Send Email Notification",
        description="Flag indicating whether to send email notification",
    )
    model_config = ConfigDict(extra="allow")


class ToolResponse(Model):
    outputs: List[Dict[str, Any]] = Field(
        default=[],
        title="Outputs",
        description="The outputs of the tool.",
    )
    output_collections: List[Dict[str, Any]] = Field(
        default=[],
        title="Output Collections",
        description="The output dataset collections of the tool.",
    )
    #    jobs: List[Union[ShowFullJobResponse, EncodedJobDetails, JobSummary]] = Field(
    jobs: List[Dict[str, Any]] = Field(
        default=[],
        title="Jobs",
        description="The jobs of the tool.",
    )
    implicit_collections: List[Dict[str, Any]] = Field(
        default=[],
        title="Implicit Collections",
        description="The implicit dataset collections of the tool.",
    )
    produces_entry_points: bool = Field(
        default=...,
        title="Produces Entry Points",
        description="Flag indicating whether the creation of the tool produces entry points.",
    )
    errors: List[Any] = Field(default=[], title="Errors", description="Job errors related to the creation of the tool.")
