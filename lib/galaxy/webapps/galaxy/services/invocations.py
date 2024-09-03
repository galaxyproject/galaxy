import logging
from typing import (
    Any,
    Dict,
    List,
    Tuple,
)

from pydantic import Field

from galaxy.celery.tasks import (
    prepare_invocation_download,
    write_invocation_to,
)
from galaxy.exceptions import (
    AdminRequiredException,
    ObjectNotFound,
)
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.histories import HistoryManager
from galaxy.managers.jobs import (
    fetch_job_states,
    invocation_job_source_iter,
)
from galaxy.managers.workflows import WorkflowsManager
from galaxy.model import (
    WorkflowInvocation,
    WorkflowInvocationStep,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.invocation import (
    CreateInvocationFromStore,
    InvocationSerializationParams,
    InvocationSerializationView,
    InvocationStep,
    WorkflowInvocationResponse,
)
from galaxy.schema.schema import (
    AsyncFile,
    AsyncTaskResultSummary,
    BcoGenerationParametersMixin,
    InvocationIndexQueryPayload,
    StoreExportPayload,
    WriteStoreToPayload,
)
from galaxy.schema.tasks import (
    GenerateInvocationDownload,
    WriteInvocationTo,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.short_term_storage import ShortTermStorageAllocator
from galaxy.webapps.galaxy.services.base import (
    async_task_summary,
    ConsumesModelStores,
    ensure_celery_tasks_enabled,
    model_store_storage_target,
    ServiceBase,
)

log = logging.getLogger(__name__)


class InvocationIndexPayload(InvocationIndexQueryPayload):
    instance: bool = Field(default=False, description="Is provided workflow id for Workflow instead of StoredWorkflow?")


class PrepareStoreDownloadPayload(StoreExportPayload, BcoGenerationParametersMixin):
    pass


class WriteInvocationStoreToPayload(WriteStoreToPayload, BcoGenerationParametersMixin):
    pass


class InvocationsService(ServiceBase, ConsumesModelStores):
    def __init__(
        self,
        security: IdEncodingHelper,
        histories_manager: HistoryManager,
        workflows_manager: WorkflowsManager,
        short_term_storage_allocator: ShortTermStorageAllocator,
    ):
        super().__init__(security=security)
        self._histories_manager = histories_manager
        self._workflows_manager = workflows_manager
        self.short_term_storage_allocator = short_term_storage_allocator

    def index(
        self, trans, invocation_payload: InvocationIndexPayload, serialization_params: InvocationSerializationParams
    ) -> Tuple[List[WorkflowInvocationResponse], int]:
        workflow_id = invocation_payload.workflow_id
        if invocation_payload.instance:
            instance = invocation_payload.instance
            invocation_payload.workflow_id = self._workflows_manager.get_stored_workflow(
                trans, workflow_id, by_stored_id=not instance
            ).id
        if invocation_payload.history_id:
            # access check
            self._histories_manager.get_accessible(
                invocation_payload.history_id, trans.user, current_history=trans.history
            )
        if not trans.user_is_admin:
            # We restrict the query to the current users' invocations
            # Endpoint requires user login, so trans.user.id is never None
            # TODO: user_id should be optional!
            user_id = trans.user.id
            if invocation_payload.user_id and invocation_payload.user_id != user_id:
                raise AdminRequiredException("Only admins can index the invocations of others")
        else:
            # Get all invocations if user is admin (and user_id is None).
            # xref https://github.com/galaxyproject/galaxy/pull/13862#discussion_r865732297
            user_id = invocation_payload.user_id
        invocations, total_matches = self._workflows_manager.build_invocations_query(
            trans,
            stored_workflow_id=invocation_payload.workflow_id,
            history_id=invocation_payload.history_id,
            job_id=invocation_payload.job_id,
            user_id=user_id,
            include_terminal=invocation_payload.include_terminal,
            limit=invocation_payload.limit,
            offset=invocation_payload.offset,
            sort_by=invocation_payload.sort_by,
            sort_desc=invocation_payload.sort_desc,
            include_nested_invocations=invocation_payload.include_nested_invocations,
            check_ownership=False,
        )
        invocation_dict = self.serialize_workflow_invocations(invocations, serialization_params)
        return invocation_dict, total_matches

    def show(self, trans, invocation_id, serialization_params, eager=False):
        wfi = self._workflows_manager.get_invocation(
            trans, invocation_id, eager, check_ownership=False, check_accessible=True
        )
        return self.serialize_workflow_invocation(wfi, serialization_params)

    def cancel(self, trans, invocation_id, serialization_params):
        wfi = self._workflows_manager.request_invocation_cancellation(trans, invocation_id)
        return self.serialize_workflow_invocation(wfi, serialization_params)

    def show_invocation_report(self, trans, invocation_id, format="json"):
        wfi_report = self._workflows_manager.get_invocation_report(trans, invocation_id, format=format)
        return wfi_report

    def show_invocation_step(self, trans, step_id) -> InvocationStep:
        wfi_step = self._workflows_manager.get_invocation_step(
            trans, step_id, check_ownership=False, check_accessible=True
        )
        return self.serialize_workflow_invocation_step(wfi_step)

    def update_invocation_step(self, trans, step_id, action):
        wfi_step = self._workflows_manager.update_invocation_step(trans, step_id, action)
        return self.serialize_workflow_invocation_step(wfi_step)

    def show_invocation_step_jobs_summary(self, trans, invocation_id) -> List[Dict[str, Any]]:
        ids = []
        types = []
        for job_source_type, job_source_id, _ in invocation_job_source_iter(trans.sa_session, invocation_id):
            ids.append(job_source_id)
            types.append(job_source_type)
        return fetch_job_states(trans.sa_session, ids, types)

    def show_invocation_jobs_summary(self, trans, invocation_id) -> Dict[str, Any]:
        ids = [invocation_id]
        types = ["WorkflowInvocation"]
        return fetch_job_states(trans.sa_session, ids, types)[0]

    def prepare_store_download(
        self, trans, invocation_id: DecodedDatabaseIdField, payload: PrepareStoreDownloadPayload
    ) -> AsyncFile:
        ensure_celery_tasks_enabled(trans.app.config)
        model_store_format = payload.model_store_format
        workflow_invocation = self._workflows_manager.get_invocation(
            trans, invocation_id, eager=True, check_ownership=False, check_accessible=True
        )
        if not workflow_invocation:
            raise ObjectNotFound()
        try:
            invocation_name = f"Invocation of {workflow_invocation.workflow.stored_workflow.name} at {workflow_invocation.create_time.isoformat()}"
        except AttributeError:
            invocation_name = f"Invocation of workflow at {workflow_invocation.create_time.isoformat()}"
        short_term_storage_target = model_store_storage_target(
            self.short_term_storage_allocator,
            invocation_name,
            model_store_format,
        )
        request = GenerateInvocationDownload(
            short_term_storage_request_id=short_term_storage_target.request_id,
            user=trans.async_request_user,
            invocation_id=workflow_invocation.id,
            galaxy_url=trans.request.url_path,
            **payload.model_dump(),
        )
        result = prepare_invocation_download.delay(request=request, task_user_id=getattr(trans.user, "id", None))
        return AsyncFile(storage_request_id=short_term_storage_target.request_id, task=async_task_summary(result))

    def write_store(
        self, trans, invocation_id: DecodedDatabaseIdField, payload: WriteInvocationStoreToPayload
    ) -> AsyncTaskResultSummary:
        ensure_celery_tasks_enabled(trans.app.config)
        workflow_invocation = self._workflows_manager.get_invocation(
            trans, invocation_id, eager=True, check_ownership=False, check_accessible=True
        )
        if not workflow_invocation:
            raise ObjectNotFound()
        request = WriteInvocationTo(
            galaxy_url=trans.request.url_path,
            user=trans.async_request_user,
            invocation_id=workflow_invocation.id,
            **payload.model_dump(),
        )
        result = write_invocation_to.delay(request=request, task_user_id=getattr(trans.user, "id", None))
        rval = async_task_summary(result)
        return rval

    def serialize_workflow_invocation(
        self,
        invocation: WorkflowInvocation,
        params: InvocationSerializationParams,
        default_view: InvocationSerializationView = InvocationSerializationView.element,
    ):
        view = params.view or default_view
        step_details = params.step_details
        legacy_job_state = params.legacy_job_state
        as_dict = invocation.to_dict(view.value, step_details=step_details, legacy_job_state=legacy_job_state)
        as_dict["messages"] = invocation.messages
        return WorkflowInvocationResponse(**as_dict)

    def serialize_workflow_invocations(
        self,
        invocations,
        params: InvocationSerializationParams,
        default_view: InvocationSerializationView = InvocationSerializationView.collection,
    ):
        return [self.serialize_workflow_invocation(i, params, default_view=default_view) for i in invocations]

    def serialize_workflow_invocation_step(
        self,
        invocation_step: WorkflowInvocationStep,
    ):
        return invocation_step.to_dict("element")

    def create_from_store(
        self,
        trans: ProvidesHistoryContext,
        payload: CreateInvocationFromStore,
        serialization_params: InvocationSerializationParams,
    ):
        history = self._histories_manager.get_owned(payload.history_id, trans.user, current_history=trans.history)
        object_tracker = self.create_objects_from_store(
            trans,
            payload,
            history=history,
        )
        return self.serialize_workflow_invocations(object_tracker.invocations_by_key.values(), serialization_params)
