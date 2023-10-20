from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from pydantic import (
    Extra,
    Field,
    Required,
    UUID4,
)

from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
)
from galaxy.schema.schema import (
    EncodedDatasetSourceId,
    EntityIdField,
    JobSummary,
    Model,
    UuidField,
)


class JobInputSummary(Model):
    has_empty_inputs: bool = Field(
        default=Required,
        title="Empty inputs",
        description="Job has empty inputs.",
    )
    has_duplicate_inputs: bool = Field(
        default=Required,
        title="Duplicate inputs",
        description="Job has duplicate inputs.",
    )


# TODO: Use Tuple again when `make update-client-api-schema` supports them
class JobErrorSummary(Model):
    # messages: List[Union[Tuple[str, str], List[str]]]
    messages: List[List[str]] = Field(
        default=Required,
        title="Error messages",
        description="The error messages for the specified job.",
    )


class JobAssociation(Model):
    name: str = Field(
        default=Required,
        title="name",
        description="The name of the associated dataset.",
    )
    dataset: EncodedDatasetSourceId = Field(
        default=Required,
        title="dataset",
        description="The associated dataset.",
    )


class ReportJobErrorPayload(Model):
    dataset_id: DecodedDatabaseIdField = Field(
        default=Required,
        title="Dataset ID",
        description="The dataset ID related to the error.",
    )
    # TODO add description
    email: Optional[str] = Field(
        default=None,
        title="Email",
        description="",
    )
    message: Optional[str] = Field(
        default=None,
        title="Message",
        description="The optional message sent with the error report.",
    )


class SearchJobsPayload(Model):
    tool_id: str = Field(
        default=Required,
        title="Tool ID",
        description="The tool ID related to the job.",
    )
    # TODO the inputs are actually a dict, but are passed as a JSON dump
    # maybe change it?
    inputs: str = Field(
        default=Required,
        title="Inputs",
        description="The inputs of the job as a JSON dump.",
    )
    state: str = Field(
        default=Required,
        title="State",
        description="The state of the job.",
    )

    class Config:
        extra = Extra.allow  # This is used for items named file_ and __file_


class EncodedJobIDs(Model):
    id: EncodedDatabaseIdField = EntityIdField
    history_id: Optional[EncodedDatabaseIdField] = Field(
        None,
        title="History ID",
        description="The encoded ID of the history associated with this item.",
    )


class EncodedDatasetJobInfo(EncodedDatasetSourceId):
    uuid: UUID4 = UuidField


class EncodedJobDetails(JobSummary, EncodedDatasetSourceId):
    command_version: str = Field(
        ...,
        title="Command Version",
        description="Tool version indicated during job execution.",
    )
    params: Any = Field(
        ...,
        title="Parameters",
        description=(
            "Object containing all the parameters of the tool associated with this job. "
            "The specific parameters depend on the tool itself."
        ),
    )
    inputs: Dict[str, EncodedDatasetJobInfo] = Field(
        {},
        title="Inputs",
        description="Dictionary mapping all the tool inputs (by name) with the corresponding dataset information.",
    )
    outputs: Dict[str, EncodedDatasetJobInfo] = Field(
        {},
        title="Outputs",
        description="Dictionary mapping all the tool outputs (by name) with the corresponding dataset information.",
    )
    # TODO add description, check type and add proper default
    copied_from_job_id: Any = Field(default=None, title="Copied from Job-ID", description="?")
    output_collections: Any = Field(default={}, title="Output collections", description="?")
