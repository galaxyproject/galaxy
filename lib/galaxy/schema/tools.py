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
    model_validator,
    UUID4,
)
from typing_extensions import (
    Annotated,
    Literal,
    Self,
)

from galaxy import exceptions
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    HDACustom,
    HDCADetailed,
    JobBaseModel,
    Model,
)

ToolOutputName = Annotated[
    str,
    Field(
        ...,
        title="Output Name",
        description="The name of the tool output",
    ),
]


class ExecuteToolPayload(Model):
    tool_id: Optional[str] = Field(
        default=None,
    )
    tool_uuid: Optional[UUID4] = Field(
        default=None,
        description="The UUID of the tool to execute.",
    )
    action: Optional[str] = Field(
        default=None,
        description="The action to perform",
    )
    tool_version: Optional[str] = Field(
        default=None,
    )
    history_id: Optional[DecodedDatabaseIdField] = Field(
        default=None,
    )

    @field_validator("inputs", mode="before", check_fields=False)
    @classmethod
    def inputs_string_to_json(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    inputs: Dict[str, Any] = Field(
        default={},
        description="The input parameters to use when executing a tool. Keys correspond to parameter names, values are the values set for these parameters. If parameter values are left unset defaults will be used if possible.",
    )
    use_cached_job: Optional[bool] = Field(
        default=False,
        description="If set to `true` an attempt is made to find an equivalent job and use its outputs, thereby skipping execution of the job on the compute infrastructure.",
    )
    preferred_object_store_id: Optional[str] = Field(
        default=None,
    )
    input_format: Optional[Literal["legacy", "21.01"]] = Field(
        default=None,
        title="Input Format",
        description="""If set to `legacy` or parameter is not set, inputs are assumed to be objects with concatenated keys for nested parameter, e.g. `{"conditional|parameter_name": "parameter_value"}`. If set to `"21.01"` inputs can be provided as nested objects, e.g `{"conditional": {"parameter_name": "parameter_value"}}`.""",
    )
    data_manager_mode: Optional[Literal["populate", "dry_run", "bundle"]] = Field(
        default=None,
    )
    send_email_notification: Optional[bool] = Field(
        default=None,
        title="Send Email Notification",
        description="Flag indicating whether to send email notification",
    )
    model_config = ConfigDict(extra="allow")


# The following models should eventually be removed as we move towards creating jobs asynchronously
# xref: https://github.com/galaxyproject/galaxy/pull/17393
class HDAToolOutput(HDACustom):
    output_name: ToolOutputName


class HDCAToolOutput(HDCADetailed):
    output_name: ToolOutputName


class ExecuteToolResponse(Model):
    outputs: List[HDAToolOutput] = Field(
        default=[],
        title="Outputs",
        description="The outputs of the job.",
    )
    output_collections: List[HDCAToolOutput] = Field(
        default=[],
        title="Output Collections",
        description="The output dataset collections of the job.",
    )
    jobs: List[JobBaseModel] = Field(
        default=[],
        title="Jobs",
        description="The jobs of the tool.",
    )
    implicit_collections: List[HDCAToolOutput] = Field(
        default=[],
        title="Implicit Collections",
        description="The implicit dataset collections of the job.",
    )
    produces_entry_points: bool = Field(
        default=...,
        title="Produces Entry Points",
        description="Flag indicating whether the creation of the tool produces entry points for interactive tools.",
    )
    errors: List[Any] = Field(default=[], title="Errors", description="Errors encountered while executing the tool.")
