from typing import (
    Optional,
    Union,
)
from uuid import uuid4

from pydantic import UUID4
from sqlalchemy import select

from galaxy.exceptions import (
    InconsistentDatabase,
    InsufficientPermissionsException,
    ItemAlreadyClaimedException,
    ObjectNotFound,
    RequestParameterMissingException,
)
from galaxy.model import (
    ToolLandingRequest as ToolLandingRequestModel,
    WorkflowLandingRequest as WorkflowLandingRequestModel,
)
from galaxy.model.base import transaction
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.schema import (
    ClaimLandingPayload,
    CreateToolLandingRequestPayload,
    CreateWorkflowLandingRequestPayload,
    LandingRequestState,
    ToolLandingRequest,
    WorkflowLandingRequest,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.util import safe_str_cmp
from .context import ProvidesUserContext

LandingRequestModel = Union[ToolLandingRequestModel, WorkflowLandingRequestModel]


class LandingRequestManager:

    def __init__(self, sa_session: galaxy_scoped_session, security: IdEncodingHelper):
        self.sa_session = sa_session
        self.security = security

    def create_tool_landing_request(self, payload: CreateToolLandingRequestPayload) -> ToolLandingRequest:
        model = ToolLandingRequestModel()
        model.tool_id = payload.tool_id
        model.tool_version = payload.tool_version
        model.request_state = payload.request_state
        model.uuid = uuid4()
        model.client_secret = payload.client_secret
        self._save(model)
        return self._tool_response(model)

    def create_workflow_landing_request(self, payload: CreateWorkflowLandingRequestPayload) -> WorkflowLandingRequest:
        model = WorkflowLandingRequestModel()
        if payload.workflow_target_type == "stored_workflow":
            model.stored_workflow_id = self.security.decode_id(payload.workflow_id)
        else:
            model.workflow_id = self.security.decode_id(payload.workflow_id)
        model.request_state = payload.request_state
        model.uuid = uuid4()
        model.client_secret = payload.client_secret
        self._save(model)
        return self._workflow_response(model)

    def claim_tool_landing_request(
        self, trans: ProvidesUserContext, uuid: UUID4, claim: Optional[ClaimLandingPayload]
    ) -> ToolLandingRequest:
        request = self._get_tool_landing_request(uuid)
        self._check_can_claim(trans, request, claim)
        request.user_id = trans.user.id
        self._save(request)
        return self._tool_response(request)

    def claim_workflow_landing_request(
        self, trans: ProvidesUserContext, uuid: UUID4, claim: Optional[ClaimLandingPayload]
    ) -> WorkflowLandingRequest:
        request = self._get_workflow_landing_request(uuid)
        self._check_can_claim(trans, request, claim)
        request.user_id = trans.user.id
        self._save(request)
        return self._workflow_response(request)

    def get_tool_landing_request(self, trans: ProvidesUserContext, uuid: UUID4) -> ToolLandingRequest:
        request = self._get_claimed_tool_landing_request(trans, uuid)
        return self._tool_response(request)

    def get_workflow_landing_request(self, trans: ProvidesUserContext, uuid: UUID4) -> WorkflowLandingRequest:
        request = self._get_claimed_workflow_landing_request(trans, uuid)
        return self._workflow_response(request)

    def _check_can_claim(
        self, trans: ProvidesUserContext, request: LandingRequestModel, claim: Optional[ClaimLandingPayload]
    ):
        if request.client_secret is not None:
            if claim is None or not claim.client_secret:
                raise RequestParameterMissingException()
            if not safe_str_cmp(request.client_secret, claim.client_secret):
                raise InsufficientPermissionsException()
        if request.user_id is not None:
            raise ItemAlreadyClaimedException()

    def _get_tool_landing_request(self, uuid: UUID4) -> ToolLandingRequestModel:
        request = self.sa_session.scalars(
            select(ToolLandingRequestModel).where(ToolLandingRequestModel.uuid == str(uuid))
        ).one_or_none()
        if request is None:
            raise ObjectNotFound()
        return request

    def _get_workflow_landing_request(self, uuid: UUID4) -> WorkflowLandingRequestModel:
        request = self.sa_session.scalars(
            select(WorkflowLandingRequestModel).where(WorkflowLandingRequestModel.uuid == str(uuid))
        ).one_or_none()
        if request is None:
            raise ObjectNotFound()
        return request

    def _get_claimed_tool_landing_request(self, trans: ProvidesUserContext, uuid: UUID4) -> ToolLandingRequestModel:
        request = self._get_tool_landing_request(uuid)
        self._check_ownership(trans, request)
        return request

    def _get_claimed_workflow_landing_request(
        self, trans: ProvidesUserContext, uuid: UUID4
    ) -> WorkflowLandingRequestModel:
        request = self._get_workflow_landing_request(uuid)
        self._check_ownership(trans, request)
        return request

    def _tool_response(self, model: ToolLandingRequestModel) -> ToolLandingRequest:
        response_model = ToolLandingRequest(
            tool_id=model.tool_id,
            tool_version=model.tool_version,
            request_state=model.request_state,
            uuid=model.uuid,
            state=self._state(model),
        )
        return response_model

    def _workflow_response(self, model: WorkflowLandingRequestModel) -> WorkflowLandingRequest:
        workflow_id: Optional[int]
        if model.stored_workflow_id is not None:
            workflow_id = model.stored_workflow_id
            target_type = "stored_workflow"
        else:
            workflow_id = model.workflow_id
            target_type = "workflow"
        if workflow_id is None:
            raise InconsistentDatabase()
        assert workflow_id
        response_model = WorkflowLandingRequest(
            workflow_id=self.security.encode_id(workflow_id),
            workflow_target_type=target_type,
            request_state=model.request_state,
            uuid=model.uuid,
            state=self._state(model),
        )
        return response_model

    def _check_ownership(self, trans: ProvidesUserContext, model: LandingRequestModel):
        if model.user_id != trans.user.id:
            raise InsufficientPermissionsException()

    def _state(self, model: LandingRequestModel) -> LandingRequestState:
        return LandingRequestState.UNCLAIMED if model.user_id is None else LandingRequestState.CLAIMED

    def _save(self, model: LandingRequestModel):
        sa_session = self.sa_session
        sa_session.add(model)
        with transaction(sa_session):
            sa_session.commit()
