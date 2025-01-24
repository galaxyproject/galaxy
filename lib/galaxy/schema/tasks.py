from typing import (
    List,
    Optional,
)
from uuid import UUID

from pydantic import Field

from galaxy.util.hash_util import HashFunctionNameEnum
from . import PdfDocumentType
from .schema import (
    BcoGenerationParametersMixin,
    DatasetSourceType,
    HistoryContentType,
    Model,
    ModelStoreFormat,
    ShortTermStoreExportPayload,
    WriteStoreToPayload,
)


class SetupHistoryExportJob(Model):
    history_id: int
    job_id: int
    store_directory: str
    include_files: bool
    include_hidden: bool
    include_deleted: bool


class PrepareDatasetCollectionDownload(Model):
    short_term_storage_request_id: UUID
    history_dataset_collection_association_id: int


class GeneratePdfDownload(Model):
    short_term_storage_request_id: UUID
    # basic markdown - Galaxy directives need to be processed before handing off to this task
    basic_markdown: str
    document_type: PdfDocumentType


# serialize user info for tasks
class RequestUser(Model):
    user_id: int
    # TODO: allow make the above optional and allow a session_id for anonymous users...
    # session_id: Optional[str]


class GenerateHistoryDownload(ShortTermStoreExportPayload):
    history_id: int
    user: RequestUser
    export_association_id: Optional[int] = None


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
    export_association_id: Optional[int] = None


class ImportModelStoreTaskRequest(Model):
    user: RequestUser
    history_id: Optional[int] = None
    source_uri: str
    for_library: bool
    model_store_format: Optional[ModelStoreFormat] = None


class MaterializeDatasetInstanceTaskRequest(Model):
    history_id: int
    user: RequestUser
    source: DatasetSourceType = Field(
        title="Source",
        description="The source of the content. Can be other history element to be copied or library elements.",
    )
    content: int = Field(
        title="Content",
        description=(
            "Depending on the `source` it can be:\n"
            "- The decoded id of the source library dataset\n"
            "- The decoded id of the HDA\n"
        ),
    )


class ComputeDatasetHashTaskRequest(Model):
    dataset_id: int
    extra_files_path: Optional[str] = None
    hash_function: HashFunctionNameEnum
    user: Optional[RequestUser] = None  # access checks should be done pre-celery so this is optional


class PurgeDatasetsTaskRequest(Model):
    dataset_ids: List[int]
