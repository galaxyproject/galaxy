from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
)

from galaxy.util.hash_util import HashFunctionNameEnum
from . import PdfDocumentType
from .schema import (
    BcoGenerationParametersMixin,
    DatasetSourceType,
    HistoryContentType,
    ModelStoreFormat,
    ShortTermStoreExportPayload,
    WriteStoreToPayload,
)


class SetupHistoryExportJob(BaseModel):
    history_id: int
    job_id: int
    store_directory: str
    include_files: bool
    include_hidden: bool
    include_deleted: bool


class PrepareDatasetCollectionDownload(BaseModel):
    short_term_storage_request_id: UUID
    history_dataset_collection_association_id: int


class GeneratePdfDownload(BaseModel):
    short_term_storage_request_id: UUID
    # basic markdown - Galaxy directives need to be processed before handing off to this task
    basic_markdown: str
    document_type: PdfDocumentType


# serialize user info for tasks
class RequestUser(BaseModel):
    user_id: int
    # TODO: allow make the above optional and allow a session_id for anonymous users...
    # session_id: Optional[str]


class GenerateHistoryDownload(ShortTermStoreExportPayload):
    history_id: int
    user: RequestUser
    export_association_id: Optional[int]


class GenerateHistoryContentDownload(ShortTermStoreExportPayload):
    content_type: HistoryContentType
    content_id: int
    user: RequestUser


class BcoGenerationTaskParametersMixin(BcoGenerationParametersMixin):
    galaxy_url: str


class GenerateInvocationDownload(ShortTermStoreExportPayload, BcoGenerationTaskParametersMixin):
    invocation_id: int
    user: RequestUser


class WriteInvocationTo(WriteStoreToPayload, BcoGenerationTaskParametersMixin):
    invocation_id: int
    user: RequestUser


class WriteHistoryContentTo(WriteStoreToPayload):
    content_type: HistoryContentType
    content_id: int
    user: RequestUser


class WriteHistoryTo(WriteStoreToPayload):
    history_id: int
    user: RequestUser
    export_association_id: Optional[int]


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


class ComputeDatasetHashTaskRequest(BaseModel):
    dataset_id: int
    extra_files_path: Optional[str]
    hash_function: HashFunctionNameEnum
    user: Optional[RequestUser]  # access checks should be done pre-celery so this is optional
