from typing import (
    List,
    Optional,
)

from pydantic import Extra

from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    EncodedDatasetSourceId,
    Model,
)


class JobInputSummary(Model):
    has_empty_inputs: bool
    has_duplicate_inputs: bool


# TODO: Use Tuple again when `make update-client-api-schema` supports them
class JobErrorSummary(Model):
    # messages: List[Union[Tuple[str, str], List[str]]]
    messages: List[List[str]]


class JobAssociation(Model):
    name: str
    dataset: EncodedDatasetSourceId


class ReportJobErrorPayload(Model):
    dataset_id: DecodedDatabaseIdField
    email: Optional[str] = None
    message: Optional[str] = None


class SearchJobsPayload(Model):
    tool_id: str
    inputs: str
    state: str

    class Config:
        extra = Extra.allow  # This is used for items named file_ and __file_
