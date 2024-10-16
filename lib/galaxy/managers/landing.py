from typing import (
    Optional,
    Union,
)
from uuid import uuid4

import yaml
from pydantic import UUID4
from sqlalchemy import select

from galaxy.exceptions import (
    InsufficientPermissionsException,
    ItemAlreadyClaimedException,
    ItemMustBeClaimed,
    ObjectNotFound,
    RequestParameterMissingException,
)
from galaxy.managers.workflows import (
    WorkflowContentsManager,
    WorkflowCreateOptions,
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
from galaxy.structured_app import StructuredApp
from galaxy.util import safe_str_cmp
from .context import ProvidesUserContext

LandingRequestModel = Union[ToolLandingRequestModel, WorkflowLandingRequestModel]


class LandingRequestManager:

    def __init__(
        self,
        sa_session: galaxy_scoped_session,
        security: IdEncodingHelper,
        workflow_contents_manager: WorkflowContentsManager,
    ):
        self.sa_session = sa_session
        self.security = security
        self.workflow_contents_manager = workflow_contents_manager

    def create_tool_landing_request(self, payload: CreateToolLandingRequestPayload, user_id=None) -> ToolLandingRequest:
        model = ToolLandingRequestModel()
        model.tool_id = payload.tool_id
        model.tool_version = payload.tool_version
        model.request_state = payload.request_state
        model.uuid = uuid4()
        model.client_secret = payload.client_secret
        model.public = payload.public
        if user_id:
            model.user_id = user_id
        self._save(model)
        return self._tool_response(model)

    def create_workflow_landing_request(self, payload: CreateWorkflowLandingRequestPayload) -> WorkflowLandingRequest:
        model = WorkflowLandingRequestModel()
        if payload.workflow_target_type == "stored_workflow":
            model.stored_workflow_id = self.security.decode_id(payload.workflow_id)
        elif payload.workflow_target_type == "workflow":
            model.workflow_id = self.security.decode_id(payload.workflow_id)
        elif payload.workflow_target_type == "trs_url":
            model.workflow_source_type = "trs_url"
            # validate this ?
            model.workflow_source = payload.workflow_id
        model.uuid = uuid4()
        model.client_secret = payload.client_secret
        model.request_state = payload.request_state
        model.public = payload.public
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
        self._ensure_workflow(trans, request)
        request.user_id = trans.user.id
        self._save(request)
        return self._workflow_response(request)

    def _ensure_workflow(self, trans: ProvidesUserContext, request: WorkflowLandingRequestModel):
        if request.workflow_source_type == "trs_url" and isinstance(trans.app, StructuredApp):
            # trans is always structured app except for unit test
            assert request.workflow_source
            trs_id, trs_version = request.workflow_source.rsplit("/", 1)
            _, trs_id, trs_version = trans.app.trs_proxy.get_trs_id_and_version_from_trs_url(request.workflow_source)
            workflow = self.workflow_contents_manager.get_workflow_by_trs_id_and_version(
                self.sa_session, trs_id=trs_id, trs_version=trs_version, user_id=trans.user and trans.user.id
            )
            if not workflow:
                data = trans.app.trs_proxy.get_version_from_trs_url(request.workflow_source)
                as_dict = yaml.safe_load(data)
                raw_workflow_description = self.workflow_contents_manager.normalize_workflow_format(trans, as_dict)
                created_workflow = self.workflow_contents_manager.build_workflow_from_raw_description(
                    trans,
                    raw_workflow_description,
                    WorkflowCreateOptions(),
                )
                workflow = created_workflow.workflow
            request.workflow_id = workflow.id

    def get_tool_landing_request(self, trans: ProvidesUserContext, uuid: UUID4) -> ToolLandingRequest:
        request = self._get_claimed_tool_landing_request(trans, uuid)
        return self._tool_response(request)

    def get_workflow_landing_request(self, trans: ProvidesUserContext, uuid: UUID4) -> WorkflowLandingRequest:
        request = self._get_claimed_workflow_landing_request(trans, uuid)
        self._ensure_workflow(trans, request)
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

        workflow_id: Optional[Union[int, str]] = None
        if model.stored_workflow_id is not None:
            workflow_id = model.stored_workflow_id
            target_type = "stored_workflow"
        elif model.workflow_id is not None:
            workflow_id = model.workflow_id
            target_type = "workflow"
        elif model.workflow_source_type == "trs_url":
            target_type = model.workflow_source_type
            workflow_id = model.workflow_source
        assert workflow_id
        response_model = WorkflowLandingRequest(
            workflow_id=self.security.encode_id(workflow_id) if isinstance(workflow_id, int) else workflow_id,
            workflow_target_type=target_type,
            request_state=model.request_state,
            uuid=model.uuid,
            state=self._state(model),
        )
        return response_model

    def _check_ownership(self, trans: ProvidesUserContext, model: LandingRequestModel):
        if not model.public and self._state(model) == LandingRequestState.UNCLAIMED:
            raise ItemMustBeClaimed
        if model.user_id and model.user_id != trans.user.id:
            raise InsufficientPermissionsException()

    def _state(self, model: LandingRequestModel) -> LandingRequestState:
        return LandingRequestState.UNCLAIMED if model.user_id is None else LandingRequestState.CLAIMED

    def _save(self, model: LandingRequestModel):
        sa_session = self.sa_session
        sa_session.add(model)
        with transaction(sa_session):
            sa_session.commit()
