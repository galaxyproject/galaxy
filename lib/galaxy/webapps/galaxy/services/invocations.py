from enum import Enum
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

from galaxy.exceptions import AdminRequiredException
from galaxy.managers.histories import HistoryManager
from galaxy.managers.workflows import WorkflowsManager
from galaxy.schema.schema import InvocationIndexQueryPayload
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.galaxy.services.base import ServiceBase


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


class InvocationsService(ServiceBase):
    def __init__(
        self, security: IdEncodingHelper, histories_manager: HistoryManager, workflows_manager: WorkflowsManager
    ):
        super().__init__(security=security)
        self._histories_manager = histories_manager
        self._workflows_manager = workflows_manager

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
        invocation_dict = self._serialize_workflow_invocations(invocations, serialization_params)
        return invocation_dict, total_matches

    def serialize_workflow_invocation(
        self,
        invocation,
        params: InvocationSerializationParams,
        default_view: InvocationSerializationView = InvocationSerializationView.element,
    ):
        view = params.view or default_view
        step_details = params.step_details
        legacy_job_state = params.legacy_job_state
        as_dict = invocation.to_dict(view, step_details=step_details, legacy_job_state=legacy_job_state)
        return self.security.encode_all_ids(as_dict, recursive=True)

    def _serialize_workflow_invocations(
        self,
        invocations,
        params: InvocationSerializationParams,
        default_view: InvocationSerializationView = InvocationSerializationView.collection,
    ):
        return list(
            map(lambda i: self.serialize_workflow_invocation(i, params, default_view=default_view), invocations)
        )
