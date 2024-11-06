import json
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
    InconsistentDatabase,
    ObjectNotFound,
)
from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.managers.histories import HistoryManager
from galaxy.managers.jobs import (
    fetch_job_states,
    get_job_metrics_for_invocation,
    invocation_job_source_iter,
    summarize_metrics,
)
from galaxy.managers.workflows import WorkflowsManager
from galaxy.model import (
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    WorkflowInvocation,
    WorkflowInvocationStep,
    WorkflowRequestInputParameter,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.invocation import (
    CreateInvocationFromStore,
    InvocationSerializationParams,
    InvocationSerializationView,
    InvocationStep,
    WorkflowInvocationRequestModel,
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

    def as_request(self, trans: ProvidesUserContext, invocation_id) -> WorkflowInvocationRequestModel:
        wfi = self._workflows_manager.get_invocation(
            trans, invocation_id, True, check_ownership=True, check_accessible=True
        )
        return self.serialize_workflow_invocation_to_request(trans, wfi)

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

    def show_invocation_metrics(self, trans: ProvidesHistoryContext, invocation_id: int):
        extended_job_metrics = get_job_metrics_for_invocation(trans.sa_session, invocation_id)
        job_metrics = []
        tool_ids = []
        step_indexes = []
        step_labels = []
        for row in extended_job_metrics:
            step_indexes.append(row[0])
            tool_ids.append(row[1])
            step_labels.append(row[2])
            job_metrics.append(row[3])
        metrics_dict_list = summarize_metrics(trans, job_metrics)
        for tool_id, step_index, step_label, metrics_dict in zip(
            tool_ids, step_indexes, step_labels, metrics_dict_list
        ):
            metrics_dict["tool_id"] = tool_id
            metrics_dict["step_index"] = step_index
            metrics_dict["step_label"] = step_label
        return metrics_dict_list

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

    def serialize_workflow_invocation_to_request(
        self, trans: ProvidesUserContext, invocation: WorkflowInvocation
    ) -> WorkflowInvocationRequestModel:
        history_id = trans.security.encode_id(invocation.history.id)
        workflow_id = trans.security.encode_id(invocation.workflow.id)
        inputs, inputs_by = invocation.recover_inputs()
        export_inputs = {}
        for key, value in inputs.items():
            if isinstance(value, HistoryDatasetAssociation):
                export_inputs[key] = {"src": "hda", "id": trans.security.encode_id(value.id)}
            elif isinstance(value, HistoryDatasetCollectionAssociation):
                export_inputs[key] = {"src": "hdca", "id": trans.security.encode_id(value.id)}
            else:
                export_inputs[key] = value

        param_types = WorkflowRequestInputParameter.types
        steps_by_id = invocation.workflow.steps_by_id

        replacement_dict = {}
        resource_params = {}
        use_cached_job = False
        preferred_object_store_id = None
        preferred_intermediate_object_store_id = None
        preferred_outputs_object_store_id = None
        step_param_map: Dict[str, Dict] = {}
        for parameter in invocation.input_parameters:
            parameter_type = parameter.type

            if parameter_type == param_types.REPLACEMENT_PARAMETERS:
                replacement_dict[parameter.name] = parameter.value
            elif parameter_type == param_types.META_PARAMETERS:
                # copy_inputs_to_history is being skipped here sort of intentionally,
                # we wouldn't want to include this on re-run.
                if parameter.name == "use_cached_job":
                    use_cached_job = parameter.value == "true"
                if parameter.name == "preferred_object_store_id":
                    preferred_object_store_id = parameter.value
                if parameter.name == "preferred_intermediate_object_store_id":
                    preferred_intermediate_object_store_id = parameter.value
                if parameter.name == "preferred_outputs_object_store_id":
                    preferred_outputs_object_store_id = parameter.value
            elif parameter_type == param_types.RESOURCE_PARAMETERS:
                resource_params[parameter.name] = parameter.value
            elif parameter_type == param_types.STEP_PARAMETERS:
                # TODO: test subworkflows and ensure this works
                step_id: int
                try:
                    step_id = int(parameter.name)
                except TypeError:
                    raise InconsistentDatabase("saved workflow step parameters not in the format expected")
                step_param_map[str(steps_by_id[step_id].order_index)] = json.loads(parameter.value)

        return WorkflowInvocationRequestModel(
            history_id=history_id,
            workflow_id=workflow_id,
            instance=True,  # this is a workflow ID and not a stored workflow ID
            inputs=export_inputs,
            inputs_by=inputs_by,
            replacement_params=None if not replacement_dict else replacement_dict,
            resource_params=None if not resource_params else resource_params,
            use_cached_job=use_cached_job,
            preferred_object_store_id=preferred_object_store_id,
            preferred_intermediate_object_store_id=preferred_intermediate_object_store_id,
            preferred_outputs_object_store_id=preferred_outputs_object_store_id,
            parameters_normalized=True,
            parameters=None if not step_param_map else step_param_map,
        )
