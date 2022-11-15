from typing import Optional

from pydantic import (
    BaseModel,
    Field,
)

from .schema import (
    DatasetSourceType,
    HistoryContentType,
    ModelStoreFormat,
    StoreExportPayload,
    WriteStoreToPayload,
)
from ..schema import PdfDocumentType


class SetupHistoryExportJob(BaseModel):
    history_id: int
    job_id: int
    store_directory: str
    include_files: bool
    include_hidden: bool
    include_deleted: bool


class PrepareDatasetCollectionDownload(BaseModel):
    short_term_storage_request_id: str
    history_dataset_collection_association_id: int


class GeneratePdfDownload(BaseModel):
    short_term_storage_request_id: str
    # basic markdown - Galaxy directives need to be processed before handing off to this task
    basic_markdown: str
    document_type: PdfDocumentType


# serialize user info for tasks
class RequestUser(BaseModel):
    user_id: int
    # TODO: allow make the above optional and allow a session_id for anonymous users...
    # session_id: Optional[str]


class GenerateHistoryDownload(StoreExportPayload):
    history_id: int
    short_term_storage_request_id: str
    user: RequestUser


class GenerateHistoryContentDownload(StoreExportPayload):
    content_type: HistoryContentType
    content_id: int
    short_term_storage_request_id: str
    user: RequestUser


class GenerateInvocationDownload(StoreExportPayload):
    invocation_id: int
    short_term_storage_request_id: str
    user: RequestUser


class WriteInvocationTo(WriteStoreToPayload):
    invocation_id: int
    user: RequestUser


class WriteHistoryContentTo(WriteStoreToPayload):
    content_type: HistoryContentType
    content_id: int
    user: RequestUser


class WriteHistoryTo(WriteStoreToPayload):
    history_id: int
    user: RequestUser


class ImportModelStoreTaskRequest(BaseModel):
    user: RequestUser
    history_id: Optional[int]
    source_uri: str
    for_library: bool
    model_store_format: Optional[ModelStoreFormat]


class MaterializeDatasetInstanceTaskRequest(BaseModel):
    history_id: int
    user: RequestUser
    source: DatasetSourceType = Field(
        None,
        title="Source",
        description="The source of the content. Can be other history element to be copied or library elements.",
    )
    content: int = Field(
        None,
        title="Content",
        description=(
            "Depending on the `source` it can be:\n"
            "- The encoded id of the source library dataset\n"
            "- The encoded id of the the HDA\n"
        ),
    )
