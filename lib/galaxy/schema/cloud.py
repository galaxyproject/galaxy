from typing import (
    List,
    Optional,
    Union,
)

from pydantic import (
    Field,
    RootModel,
)
from typing_extensions import Literal

from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    DatasetSummary,
    Model,
)


class InputArguments(Model):
    dbkey: Optional[str] = Field(
        default="?",
        title="Database Key",
        description="Sets the database key of the objects being fetched to Galaxy.",
    )
    file_type: Optional[str] = Field(
        default="auto",
        title="File Type",
        description="Sets the Galaxy datatype (e.g., `bam`) for the objects being fetched to Galaxy. See the following link for a complete list of Galaxy data types: https://galaxyproject.org/learn/datatypes/.",
    )
    to_posix_lines: Optional[Union[Literal["Yes"], bool]] = Field(
        default="Yes",
        title="POSIX line endings",
        description="A boolean value ('true' or 'false'); if 'Yes', converts universal line endings to POSIX line endings. Set to 'False' if you upload a gzip, bz2 or zip archive containing a binary file.",
    )
    space_to_tab: Optional[bool] = Field(
        default=False,
        title="Spaces to tabs",
        description="A boolean value ('true' or 'false') that sets if spaces should be converted to tab in the objects being fetched to Galaxy. Applicable only if `to_posix_lines` is True",
    )


class CloudObjects(Model):
    history_id: DecodedDatabaseIdField = Field(
        default=...,
        title="History ID",
        description="The ID of history to which the object should be received to.",
    )
    bucket: str = Field(
        default=...,
        title="Bucket",
        description="The name of a bucket from which data should be fetched from (e.g., a bucket name on AWS S3).",
    )
    objects: List[str] = Field(
        default=...,
        title="Objects",
        description="A list of the names of objects to be fetched.",
    )
    authz_id: DecodedDatabaseIdField = Field(
        default=...,
        title="Authentication ID",
        description="The ID of CloudAuthz to be used for authorizing access to the resource provider. You may get a list of the defined authorizations via `/api/cloud/authz`. Also, you can use `/api/cloud/authz/create` to define a new authorization.",
    )
    input_args: Optional[InputArguments] = Field(
        default=None,
        title="Input arguments",
        description="A summary of the input arguments, which is optional and will default to {}.",
    )


class CloudDatasets(Model):
    history_id: DecodedDatabaseIdField = Field(
        default=...,
        title="History ID",
        description="The ID of history from which the object should be downloaded",
    )
    bucket: str = Field(
        default=...,
        title="Bucket",
        description="The name of a bucket to which data should be sent (e.g., a bucket name on AWS S3).",
    )
    authz_id: DecodedDatabaseIdField = Field(
        default=...,
        title="Authentication ID",
        description="The ID of CloudAuthz to be used for authorizing access to the resource provider. You may get a list of the defined authorizations via `/api/cloud/authz`. Also, you can use `/api/cloud/authz/create` to define a new authorization.",
    )
    dataset_ids: Optional[List[DecodedDatabaseIdField]] = Field(
        default=None,
        title="Objects",
        description="A list of dataset IDs belonging to the specified history that should be sent to the given bucket. If not provided, Galaxy sends all the datasets belonging the specified history.",
    )
    overwrite_existing: Optional[bool] = Field(
        default=False,
        title="Spaces to tabs",
        description="A boolean value. If set to 'True', and an object with same name of the dataset to be sent already exist in the bucket, Galaxy replaces the existing object with the dataset to be sent. If set to 'False', Galaxy appends datetime to the dataset name to prevent overwriting an existing object.",
    )


class CloudDatasetsResponse(Model):
    sent_dataset_labels: List[str] = Field(
        default=...,
        title="Send datasets",
        description="The datasets for which Galaxy succeeded to create (and queue) send job",
    )
    failed_dataset_labels: List[str] = Field(
        default=...,
        title="Failed datasets",
        description="The datasets for which Galaxy failed to create (and queue) send job",
    )
    bucket_name: str = Field(
        default=...,
        title="Bucket",
        description="The name of bucket to which the listed datasets are queued to be sent",
    )


class StatusCode(Model):
    detail: str = Field(
        default=...,
        title="Detail",
        description="The detail to expand on the status code",
    )
    status: int = Field(
        default=...,
        title="Code",
        description="The actual status code",
    )


class DatasetSummaryList(RootModel):
    root: List[DatasetSummary]
