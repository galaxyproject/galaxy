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
    EncodedDataItemSourceId,
    EntityIdField,
    JobState,
    JobSummary,
    Model,
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
        description="Name of the job parameter.",
    )
    dataset: EncodedDataItemSourceId = Field(
        default=Required,
        title="dataset",
        description="Reference to the associated item.",
    )


class ReportJobErrorPayload(Model):
    dataset_id: DecodedDatabaseIdField = Field(
        default=Required,
        title="History Dataset Association ID",
        description="The History Dataset Association ID related to the error.",
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
    state: JobState = Field(
        default=Required,
        title="State",
        description="Current state of the job.",
    )

    class Config:
        extra = Extra.allow  # This is used for items named file_ and __file_


class DeleteJobPayload(Model):
    message: Optional[str] = Field(
        default=None,
        title="Job message",
        description="Stop message",
    )


class EncodedDatasetJobInfo(EncodedDataItemSourceId):
    uuid: Optional[UUID4] = Field(
        default=None,
        deprecated=True,
        title="UUID",
        description="Universal unique identifier for this dataset. In this context the uuid is optional and marked as deprecated.",
    )


class EncodedJobIDs(Model):
    id: EncodedDatabaseIdField = EntityIdField
    history_id: Optional[EncodedDatabaseIdField] = Field(
        None,
        title="History ID",
        description="The encoded ID of the history associated with this item.",
    )


class EncodedJobDetails(JobSummary, EncodedJobIDs):
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
        description="Dictionary mapping all the tool inputs (by name) to the corresponding data references.",
    )
    outputs: Dict[str, EncodedDatasetJobInfo] = Field(
        {},
        title="Outputs",
        description="Dictionary mapping all the tool outputs (by name) to the corresponding data references.",
    )
    # TODO add description, check type and add proper default
    copied_from_job_id: Optional[EncodedDatabaseIdField] = Field(
        default=None, title="Copied from Job-ID", description="Reference to cached job if job execution was cached."
    )
    output_collections: Any = Field(default=None, title="Output collections", description="?")


class JobDestinationParams(Model):
    # TODO add description, check type and add proper default
    runner: str = Field(default=Required, title="Runner", description="Job runner class", alias="Runner")
    runner_job_id: str = Field(
        default=Required,
        title="Runner Job ID",
        description="ID assigned to submitted job by external job running system",
        alias="Runner Job ID",
    )
    handler: str = Field(default=Required, title="Handler", description="?", alias="Handler")


class JobOutput(Model):
    label: Any = Field(default=Required, title="Output label", description="The output label")  # check if this is true
    value: EncodedDataItemSourceId = Field(default=Required, title="dataset", description="The associated dataset.")


class JobParameter(Model):
    text: str = Field(
        default=Required,
        title="Text",
        description="Text associated with the job parameter.",
    )
    depth: int = Field(
        default=Required,
        title="Depth",
        description="The depth of the job parameter.",
    )
    value: Any = Field(default=Required, title="Value", description="The values of the job parameter")
    notes: Optional[str] = Field(default=None, title="notes", description="Notes associated with the job parameter.")


class JobDisplayParametersSummary(Model):
    parameters: List[JobParameter] = Field(
        default=Required, title="Parameters", description="The parameters of the job in a nested format."
    )
    has_parameter_errors: bool = Field(
        default=Required, title="Has parameter errors", description="The job has parameter errors"
    )
    outputs: Dict[str, List[JobOutput]] = Field(
        default=Required,
        title="Outputs",
        description="Dictionary mapping all the tool outputs (by name) with the corresponding dataset information in a nested format.",
    )
