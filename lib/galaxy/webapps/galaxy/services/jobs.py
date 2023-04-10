import logging
from enum import Enum
from typing import (
    Any,
    Dict,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)

from galaxy import (
    exceptions,
    model,
)
from galaxy.celery.tasks import queue_jobs
from galaxy.managers import hdas
from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.managers.histories import HistoryManager
from galaxy.managers.jobs import (
    JobManager,
    JobSearch,
    view_show_job,
)
from galaxy.model import ToolRequest
from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
)
from galaxy.schema.schema import (
    AsyncTaskResultSummary,
    JobIndexQueryPayload,
)
from galaxy.schema.tasks import (
    QueueJobs,
    ToolSource,
)
from galaxy.tool_util.parameters import (
    decode,
    RequestToolState,
)
from galaxy.webapps.galaxy.services.base import async_task_summary
from .tools import (
    ToolRunReference,
    validate_tool_for_running,
)

log = logging.getLogger(__name__)


class JobRequest(BaseModel):
    tool_id: Optional[str] = Field(title="tool_id", description="TODO")
    tool_uuid: Optional[str] = Field(title="tool_uuid", description="TODO")
    tool_version: Optional[str] = Field(title="tool_version", description="TODO")
    history_id: Optional[DecodedDatabaseIdField] = Field("history_id", description="TODO")
    inputs: Optional[Dict[str, Any]] = Field(default_factory=lambda: {}, title="Inputs", description="TODO")
    use_cached_jobs: Optional[bool] = Field(default=None, title="use_cached_jobs")
    rerun_remap_job_id: Optional[DecodedDatabaseIdField] = Field("rerun_remap_job_id", description="TODO")
    send_email_notification: bool = Field(default=False, title="Send Email Notification", description="TODO")


class JobCreateResponse(BaseModel):
    tool_request_id: EncodedDatabaseIdField
    task_result: AsyncTaskResultSummary


class JobIndexViewEnum(str, Enum):
    collection = "collection"
    admin_job_list = "admin_job_list"


class JobIndexPayload(JobIndexQueryPayload):
    view: JobIndexViewEnum = JobIndexViewEnum.collection


class JobsService:
    job_manager: JobManager
    job_search: JobSearch
    hda_manager: hdas.HDAManager
    history_manager: HistoryManager

    def __init__(
        self,
        job_manager: JobManager,
        job_search: JobSearch,
        hda_manager: hdas.HDAManager,
        history_manager: HistoryManager,
    ):
        self.job_manager = job_manager
        self.job_search = job_search
        self.hda_manager = hda_manager
        self.history_manager = history_manager

    def show(
        self,
        trans: ProvidesUserContext,
        id: DecodedDatabaseIdField,
        full: bool = False,
    ) -> Dict[str, Any]:
        job = self.job_manager.get_accessible_job(trans, id)
        return view_show_job(trans, job, bool(full))

    def index(
        self,
        trans: ProvidesUserContext,
        payload: JobIndexPayload,
    ):
        security = trans.security
        is_admin = trans.user_is_admin
        if payload.view == JobIndexViewEnum.admin_job_list:
            payload.user_details = True
        user_details = payload.user_details
        if payload.view == JobIndexViewEnum.admin_job_list and not is_admin:
            raise exceptions.AdminRequiredException("Only admins can use the admin_job_list view")
        query = self.job_manager.index_query(trans, payload)
        out = []
        view = payload.view
        for job in query.yield_per(model.YIELD_PER_ROWS):
            job_dict = job.to_dict(view, system_details=is_admin)
            j = security.encode_all_ids(job_dict, True)
            if view == JobIndexViewEnum.admin_job_list:
                j["decoded_job_id"] = job.id
            if user_details:
                j["user_email"] = job.get_user_email()
            out.append(j)

        return out

    def create(self, trans: ProvidesHistoryContext, job_request: JobRequest) -> JobCreateResponse:
        tool_run_reference = ToolRunReference(job_request.tool_id, job_request.tool_uuid, job_request.tool_version)
        tool = validate_tool_for_running(trans, tool_run_reference)
        history_id = job_request.history_id
        target_history = None
        if history_id is not None:
            target_history = self.history_manager.get_owned(history_id, trans.user, current_history=trans.history)
        inputs = job_request.inputs
        request_state = RequestToolState(inputs or {})
        request_state.validate(tool)
        request_internal_state = decode(request_state, tool, trans.security.decode_id)
        tool_request = ToolRequest()
        # TODO: hash and such...
        tool_request.request = request_internal_state.input_state
        tool_request.state = ToolRequest.states.NEW
        tool_request.history = target_history
        trans.sa_session.add(tool_request)
        trans.sa_session.flush()
        tool_request_id = tool_request.id
        tool_source = ToolSource(
            raw_tool_source=tool.tool_source.to_string(),
            tool_dir=tool.tool_dir,
        )
        task_request = QueueJobs(
            user=trans.async_request_user,
            history_id=target_history and target_history.id,
            tool_source=tool_source,
            use_cached_jobs=job_request.use_cached_jobs or False,
            tool_request_id=tool_request_id,
        )
        result = queue_jobs.delay(request=task_request)
        return JobCreateResponse(
            **{
                "tool_request_id": DecodedDatabaseIdField.encode(tool_request_id),
                "task_result": async_task_summary(result),
            }
        )
