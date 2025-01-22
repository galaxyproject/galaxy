import json
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import (
    ConfigDict,
    Field,
    field_validator,
    UUID4,
)
from typing_extensions import Literal

from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
)
from galaxy.schema.schema import (
    DataItemSourceType,
    EncodedDataItemSourceId,
    EncodedJobParameterHistoryItem,
    JobMetricCollection,
    JobState,
    JobSummary,
    Model,
)

class ReportToolErrorPayload(Model):
    # tool_id: DecodedDatabaseIdField = Field(
    tool_id: str = Field(
        default=...,
        # default=None,
        title="Tool ID",
        description="The Tool ID related to the error.",
    )
    email: Optional[str] = Field(
        default=None,
        title="Email",
        description="Email address for communication with the user. Only required for anonymous users.",
    )
    message: Optional[str] = Field(
        default=None,
        title="Message",
        description="The optional message sent with the error report.",
    )
