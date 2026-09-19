from enum import Enum
from typing import (
    Literal,
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
    user_id: int | None = None
    galaxy_session_id: int | None = None


class GenerateHistoryDownload(ShortTermStoreExportPayload):
    history_id: int
    user: RequestUser
    export_association_id: int | None = None


class GenerateHistoryContentDownload(ShortTermStoreExportPayload):
    content_type: HistoryContentType
    content_id: int
    user: RequestUser


class BcoGenerationTaskParametersMixin(BcoGenerationParametersMixin):
    galaxy_url: str


class GenerateInvocationDownload(ShortTermStoreExportPayload, BcoGenerationTaskParametersMixin):
    invocation_id: int
    user: RequestUser
    export_association_id: int | None = None


class WriteInvocationTo(WriteStoreToPayload, BcoGenerationTaskParametersMixin):
    invocation_id: int
    user: RequestUser
    export_association_id: int | None = None


class WriteHistoryContentTo(WriteStoreToPayload):
    content_type: HistoryContentType
    content_id: int
    user: RequestUser


class WriteHistoryTo(WriteStoreToPayload):
    history_id: int
    user: RequestUser
    export_association_id: int | None = None


class ImportModelStoreTaskRequest(Model):
    user: RequestUser
    history_id: int | None = None
    source_uri: str
    for_library: bool
    model_store_format: ModelStoreFormat | None = None


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
    extra_files_path: str | None = None
    hash_function: HashFunctionNameEnum
    user: RequestUser | None = None  # access checks should be done pre-celery so this is optional


class CopyDatasetsPayloadSourceEntry(Model):
    id: str
    type: str


class CopyDatasetsPayload(Model):
    source_content: list[CopyDatasetsPayloadSourceEntry]
    target_history_ids: list[str] | None = None
    target_history_name: str | None = None


class CopyDatasetsResponse(Model):
    history_ids: list[str]


class PurgeDatasetsTaskRequest(Model):
    dataset_ids: list[int]


class PurgeHistoryDatasetsTaskRequest(Model):
    history_id: int
    preserve_owner_update_time: bool = False


class TaskState(str, Enum):
    """Enum representing the possible states of a task."""

    PENDING = "PENDING"
    """The task is waiting for execution."""

    STARTED = "STARTED"
    """The task has been started."""

    RETRY = "RETRY"
    """The task is to be retried, possibly because of failure."""

    FAILURE = "FAILURE"
    """The task raised an exception, or has exceeded the retry limit."""

    SUCCESS = "SUCCESS"
    """The task executed successfully."""


class TaskResult(Model):
    """Contains information about the result of an asynchronous task."""

    state: TaskState = Field(
        title="State",
        description="The current state of the task.",
    )
    result: str = Field(
        title="Result",
        description="The result message of the task. Empty if the task is still running. If the task failed, this will contain the exception message.",
    )


TOOL_SOURCE_CLASS = Literal["XmlToolSource", "YamlToolSource", "CwlToolSource"]


class ToolSource(Model):
    raw_tool_source: str
    tool_dir: str | None = None
    tool_source_class: TOOL_SOURCE_CLASS = "XmlToolSource"
    tool_id: str | None = None


class QueueJobs(Model):
    tool_source: ToolSource
    tool_request_id: int  # links to request ("incoming") and history
    user: RequestUser  # TODO: test anonymous users through this submission path
    use_cached_jobs: bool
    rerun_remap_job_id: int | None  # link to a job to rerun & remap
    preferred_object_store_id: str | None = None
    tags: list[str] | None = None
    data_manager_mode: str | None = None
    send_email_notification: bool = False
    credentials_context: list[dict] | None = None
    dynamic_tool_id: int | None = None  # link to DynamicTool for custom/user tools
