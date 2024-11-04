import logging
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
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
from galaxy.managers.base import security_check
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
from galaxy.managers.tools import ToolRunReference
from galaxy.model import (
    Job,
    ToolRequest,
    ToolSource as ToolSourceModel,
)
from galaxy.model.base import transaction
from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
)
from galaxy.schema.jobs import (
    JobAssociation,
    JobOutputCollectionAssociation,
)
from galaxy.schema.schema import (
    AsyncTaskResultSummary,
    JobIndexQueryPayload,
)
from galaxy.schema.tasks import (
    QueueJobs,
    ToolSource,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.tool_util.parameters import (
    decode,
    RequestToolState,
)
from galaxy.webapps.galaxy.services.base import (
    async_task_summary,
    ServiceBase,
)
from .tools import validate_tool_for_running

log = logging.getLogger(__name__)


class JobRequest(BaseModel):
    tool_id: Optional[str] = Field(default=None, title="tool_id", description="TODO")
    tool_uuid: Optional[str] = Field(default=None, title="tool_uuid", description="TODO")
    tool_version: Optional[str] = Field(default=None, title="tool_version", description="TODO")
    history_id: Optional[DecodedDatabaseIdField] = Field(default=None, title="history_id", description="TODO")
    inputs: Optional[Dict[str, Any]] = Field(default_factory=lambda: {}, title="Inputs", description="TODO")
    use_cached_jobs: Optional[bool] = Field(default=None, title="use_cached_jobs")
    rerun_remap_job_id: Optional[DecodedDatabaseIdField] = Field(
        default=None, title="rerun_remap_job_id", description="TODO"
    )
    send_email_notification: bool = Field(default=False, title="Send Email Notification", description="TODO")


class JobCreateResponse(BaseModel):
    tool_request_id: EncodedDatabaseIdField
    task_result: AsyncTaskResultSummary


class JobIndexViewEnum(str, Enum):
    collection = "collection"
    admin_job_list = "admin_job_list"


class JobIndexPayload(JobIndexQueryPayload):
    view: JobIndexViewEnum = JobIndexViewEnum.collection


class JobsService(ServiceBase):
    job_manager: JobManager
    job_search: JobSearch
    hda_manager: hdas.HDAManager
    history_manager: HistoryManager

    def __init__(
        self,
        security: IdEncodingHelper,
        job_manager: JobManager,
        job_search: JobSearch,
        hda_manager: hdas.HDAManager,
        history_manager: HistoryManager,
    ):
        super().__init__(security=security)
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
        job = self.job_manager.get_accessible_job(
            trans,
            id,
        )
        return view_show_job(trans, job, bool(full))

    def index(
        self,
        trans: ProvidesUserContext,
        payload: JobIndexPayload,
    ):
        is_admin = trans.user_is_admin
        view = payload.view
        if view == JobIndexViewEnum.admin_job_list:
            payload.user_details = True
        user_details = payload.user_details
        decoded_user_id = payload.user_id
        if not is_admin:
            self._check_nonadmin_access(view, user_details, decoded_user_id, trans.user and trans.user.id)

        check_security_of_jobs = (
            payload.invocation_id is not None
            or payload.implicit_collection_jobs_id is not None
            or payload.history_id is not None
        )
        jobs = self.job_manager.index_query(trans, payload)
        out: List[Dict[str, Any]] = []
        for job in jobs.yield_per(model.YIELD_PER_ROWS):
            # TODO: optimize if this crucial
            if check_security_of_jobs and not security_check(trans, job.history, check_accessible=True):
                raise exceptions.ItemAccessibilityException("Cannot access the request job objects.")
            job_dict = job.to_dict(view.value, system_details=is_admin)
            if view == JobIndexViewEnum.admin_job_list:
                job_dict["decoded_job_id"] = job.id
            if user_details:
                job_dict["user_email"] = job.get_user_email()
            out.append(job_dict)

        return out

    def _check_nonadmin_access(
        self,
        view: JobIndexViewEnum,
        user_details: bool,
        decoded_user_id: Optional[DecodedDatabaseIdField],
        trans_user_id: Optional[int],
    ):
        """Verify admin-only resources are not being accessed."""
        if view == JobIndexViewEnum.admin_job_list:
            raise exceptions.AdminRequiredException("Only admins can use the admin_job_list view")
        if user_details:
            raise exceptions.AdminRequiredException("Only admins can index the jobs with user details enabled")
        if decoded_user_id is not None and decoded_user_id != trans_user_id:
            raise exceptions.AdminRequiredException("Only admins can index the jobs of others")

    def get_job(
        self,
        trans: ProvidesUserContext,
        job_id: Optional[int] = None,
        dataset_id: Optional[int] = None,
        hda_ldda: str = "hda",
    ) -> Job:
        if job_id is not None:
            return self.job_manager.get_accessible_job(trans, decoded_job_id=job_id)
        elif dataset_id is not None:
            # Following checks dataset accessible
            if hda_ldda == "hda":
                dataset_instance = self.hda_manager.get_accessible(id=dataset_id, user=trans.user)
            else:
                dataset_instance = self.hda_manager.ldda_manager.get(trans, id=dataset_id)
            if not dataset_instance.creating_job:
                raise ValueError("No job found for dataset id")
            return dataset_instance.creating_job
        else:
            # Raise an exception if neither job_id nor dataset_id is provided
            raise ValueError("Either job_id or dataset_id must be provided.")

    def dictify_associations(self, trans, *association_lists) -> List[JobAssociation]:
        rval: List[JobAssociation] = []
        for association_list in association_lists:
            rval.extend(self.__dictify_association(trans, a) for a in association_list)
        return rval

    def __dictify_association(self, trans, job_dataset_association) -> JobAssociation:
        dataset_dict = None
        if dataset := job_dataset_association.dataset:
            if isinstance(dataset, model.HistoryDatasetAssociation):
                dataset_dict = {"src": "hda", "id": dataset.id}
            else:
                dataset_dict = {"src": "ldda", "id": dataset.id}
        return JobAssociation(name=job_dataset_association.name, dataset=dataset_dict)

    def dictify_output_collection_associations(self, trans, job: model.Job) -> List[JobOutputCollectionAssociation]:
        output_associations: List[JobOutputCollectionAssociation] = []
        for job_output_collection_association in job.output_dataset_collection_instances:
            ref_dict = {"src": "hdca", "id": job_output_collection_association.dataset_collection_id}
            output_associations.append(
                JobOutputCollectionAssociation(
                    name=job_output_collection_association.name,
                    dataset_collection_instance=ref_dict,
                )
            )
        return output_associations

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
        tool_source_model = ToolSourceModel(
            source=[p.model_dump() for p in tool.parameters],
            hash="TODO",
        )
        tool_request.request = request_internal_state.input_state
        tool_request.tool_source = tool_source_model
        tool_request.state = ToolRequest.states.NEW
        tool_request.history = target_history
        sa_session = trans.sa_session
        sa_session.add(tool_source_model)
        sa_session.add(tool_request)
        with transaction(sa_session):
            sa_session.commit()
        tool_request_id = tool_request.id
        tool_source = ToolSource(
            raw_tool_source=tool.tool_source.to_string(),
            tool_dir=tool.tool_dir,
        )
        task_request = QueueJobs(
            user=trans.async_request_user,
            history_id=target_history and target_history.id,
            tool_source=tool_source,
            tool_request_id=tool_request_id,
            use_cached_jobs=job_request.use_cached_jobs or False,
            rerun_remap_job_id=job_request.rerun_remap_job_id,
        )
        result = queue_jobs.delay(request=task_request)
        return JobCreateResponse(
            **{
                "tool_request_id": tool_request_id,
                "task_result": async_task_summary(result),
            }
        )
