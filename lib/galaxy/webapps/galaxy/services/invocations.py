import logging
from enum import Enum
from tempfile import NamedTemporaryFile
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from pydantic import (
    BaseModel,
    Field,
)

from galaxy.celery.tasks import (
    prepare_invocation_download,
    write_invocation_to,
)
from galaxy.exceptions import (
    AdminRequiredException,
    ObjectNotFound,
)
from galaxy.managers.histories import HistoryManager
from galaxy.managers.workflows import WorkflowsManager
from galaxy.model import WorkflowInvocation
from galaxy.model.store import (
    BcoExportOptions,
    get_export_store_factory,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.invocation import InvocationMessageResponseModel
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
from galaxy.web.short_term_storage import ShortTermStorageAllocator
from galaxy.webapps.galaxy.services.base import (
    async_task_summary,
    ensure_celery_tasks_enabled,
    model_store_storage_target,
    ServiceBase,
)

log = logging.getLogger(__name__)


class InvocationSerializationView(str, Enum):
    element = "element"
    collection = "collection"


class InvocationSerializationParams(BaseModel):
    """Contains common parameters for customizing model serialization."""

    view: Optional[InvocationSerializationView] = Field(
        default=None,
        title="View",
        description=(
            "The name of the view used to serialize this item. "
            "This will return a predefined set of attributes of the item."
        ),
        example="element",
    )
    step_details: bool = Field(
        default=False, title="Include step details", description="Include details for individual invocation steps."
    )
    legacy_job_state: bool = Field(
        default=False,
        deprecated=True,
    )


class InvocationIndexPayload(InvocationIndexQueryPayload):
    instance: bool = Field(default=False, description="Is provided workflow id for Workflow instead of StoredWorkflow?")


class PrepareStoreDownloadPayload(StoreExportPayload, BcoGenerationParametersMixin):
    pass


class WriteInvocationStoreToPayload(WriteStoreToPayload, BcoGenerationParametersMixin):
    pass


class InvocationsService(ServiceBase):
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
    ) -> Tuple[List[Dict[str, Any]], int]:
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
        )
        invocation_dict = self.serialize_workflow_invocations(invocations, serialization_params)
        return invocation_dict, total_matches

    def prepare_store_download(
        self, trans, invocation_id: DecodedDatabaseIdField, payload: PrepareStoreDownloadPayload
    ) -> AsyncFile:
        ensure_celery_tasks_enabled(trans.app.config)
        model_store_format = payload.model_store_format
        workflow_invocation = self._workflows_manager.get_invocation(trans, invocation_id, eager=True)
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
            galaxy_url=trans.request.base,
            **payload.dict(),
        )
        result = prepare_invocation_download.delay(request=request)
        return AsyncFile(storage_request_id=short_term_storage_target.request_id, task=async_task_summary(result))

    def write_store(
        self, trans, invocation_id: DecodedDatabaseIdField, payload: WriteInvocationStoreToPayload
    ) -> AsyncTaskResultSummary:
        ensure_celery_tasks_enabled(trans.app.config)
        workflow_invocation = self._workflows_manager.get_invocation(trans, invocation_id, eager=True)
        if not workflow_invocation:
            raise ObjectNotFound()
        request = WriteInvocationTo(
            galaxy_url=trans.request.base,
            user=trans.async_request_user,
            invocation_id=workflow_invocation.id,
            **payload.dict(),
        )
        result = write_invocation_to.delay(request=request)
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
        as_dict = invocation.to_dict(view, step_details=step_details, legacy_job_state=legacy_job_state)
        as_dict = self.security.encode_all_ids(as_dict, recursive=True)
        as_dict["messages"] = [
            InvocationMessageResponseModel.parse_obj(message).__root__.dict() for message in invocation.messages
        ]
        return as_dict

    def serialize_workflow_invocations(
        self,
        invocations,
        params: InvocationSerializationParams,
        default_view: InvocationSerializationView = InvocationSerializationView.collection,
    ):
        return list(
            map(lambda i: self.serialize_workflow_invocation(i, params, default_view=default_view), invocations)
        )

    # TODO: remove this after 23.1 release
    def deprecated_generate_invocation_bco(
        self,
        trans,
        invocation_id: DecodedDatabaseIdField,
        export_options: BcoExportOptions,
    ):
        workflow_invocation = self._workflows_manager.get_invocation(trans, invocation_id, eager=True)
        if not workflow_invocation:
            raise ObjectNotFound()

        with NamedTemporaryFile() as export_target:
            with get_export_store_factory(trans.app, "bco.json", bco_export_options=export_options)(
                export_target.name
            ) as export_store:
                export_store.export_workflow_invocation(workflow_invocation)
                export_target.seek(0)
            return export_target.read()
