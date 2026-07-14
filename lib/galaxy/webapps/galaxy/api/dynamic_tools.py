import logging
from datetime import datetime
from typing import (
    Any,
    Literal,
)

from fastapi import Response
from pydantic import BaseModel

from galaxy.exceptions import (
    MessageException,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.managers.tools import (
    DynamicToolManager,
    tool_payload_to_tool,
)
from galaxy.model import User
from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
)
from galaxy.tool_util.parameters import input_models_for_tool_source
from galaxy.tool_util.parameters.convert import cwl_runtime_model
from galaxy.tool_util.parser.yaml import YamlToolSource
from galaxy.tool_util_models import (
    lift_user_tool_source,
    UserToolSource,
)
from galaxy.tool_util_models.dynamic_tool_models import (
    DynamicToolPayload,
    DynamicUnprivilegedToolCreatePayload,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    DependsOnUser,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["dynamic_tools"])

DatabaseIdOrUUID = DecodedDatabaseIdField | str


def _set_lift_headers(response: Response, status: str, errors: list[str]) -> None:
    """Surface lift status as response headers so consumers can react without
    parsing the response body. Headers are computed dynamically per request and
    are intentionally not declared in the OpenAPI schema."""
    if status == "ok" or not errors:
        return
    if status == "lifted":
        compact = ",".join(errors)
        response.headers["X-Galaxy-Deprecated-Fields"] = compact
        response.headers["Warning"] = f'299 - "Some conventions are no longer valid; ignored on read: {compact}"'
    elif status == "invalid":
        compact = "; ".join(errors)
        response.headers["X-Galaxy-Schema-Errors"] = compact
        response.headers["Warning"] = f'299 - "Stored tool no longer satisfies schema: {compact}"'


class UnprivilegedToolResponse(BaseModel):
    id: EncodedDatabaseIdField
    uuid: str
    active: bool
    hidden: bool
    tool_id: str | None
    tool_format: str | None
    create_time: datetime
    # Either a strict UserToolSource (status="ok" or "lifted") or the raw
    # stored dict (status="invalid"). Consumers narrow on `representation_status`.
    representation: UserToolSource | dict[str, Any]
    representation_status: Literal["ok", "lifted", "invalid"] = "ok"
    representation_errors: list[str] = []


def _build_unprivileged_tool_response(d: dict[str, Any]) -> UnprivilegedToolResponse:
    """Run the lift over the stored representation and assemble the response.
    This is the single place where the lift result is unpacked, so the helper's
    invariants (status='ok' → strict model, 'lifted' → strict model + dropped
    paths, 'invalid' → raw dict + error summary) are enforced exactly once."""
    raw_representation = d.get("representation") or {}
    status, representation, errors = lift_user_tool_source(raw_representation)
    return UnprivilegedToolResponse(
        id=d["id"],
        uuid=d["uuid"],
        active=d["active"],
        hidden=d["hidden"],
        tool_id=d.get("tool_id"),
        tool_format=d.get("tool_format"),
        create_time=d["create_time"],
        representation=representation,
        representation_status=status,
        representation_errors=errors,
    )


@router.cbv
class UnprivilegedToolsApi:
    # Almost identical to dynamic tools api, but operates with tool ids
    # and is scoped to to individual user and never adds to global toolbox
    dynamic_tools_manager: DynamicToolManager = depends(DynamicToolManager)

    @router.get("/api/unprivileged_tools", response_model_exclude_defaults=True)
    def index(
        self,
        response: Response,
        active: bool = True,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> list[UnprivilegedToolResponse]:
        if not trans.user:
            return []
        result = [
            _build_unprivileged_tool_response(t.to_dict())
            for t in self.dynamic_tools_manager.list_unprivileged_tools(trans.user, active=active)
        ]
        # Aggregate header: any tool with drift surfaces it on the index call.
        worst = "ok"
        aggregate: list[str] = []
        for tool in result:
            if tool.representation_status == "invalid":
                worst = "invalid"
            elif tool.representation_status == "lifted" and worst == "ok":
                worst = "lifted"
            aggregate.extend(tool.representation_errors)
        _set_lift_headers(response, worst, aggregate)
        return result

    @router.get("/api/unprivileged_tools/{uuid}", response_model_exclude_defaults=True)
    def show(self, response: Response, uuid: str, user: User = DependsOnUser) -> UnprivilegedToolResponse:
        dynamic_tool = self.dynamic_tools_manager.get_unprivileged_tool_by_uuid(user, uuid)
        if dynamic_tool is None:
            raise ObjectNotFound()
        tool = _build_unprivileged_tool_response(dynamic_tool.to_dict())
        _set_lift_headers(response, tool.representation_status, tool.representation_errors)
        return tool

    @router.post("/api/unprivileged_tools", response_model_exclude_defaults=True)
    def create(
        self, payload: DynamicUnprivilegedToolCreatePayload, user: User = DependsOnUser
    ) -> UnprivilegedToolResponse:
        dynamic_tool = self.dynamic_tools_manager.create_unprivileged_tool(
            user,
            payload,
        )
        # Just-created tools are validated through strict input, so the lift
        # is a no-op here, but going through the same builder keeps behavior
        # uniform.
        return _build_unprivileged_tool_response(dynamic_tool.to_dict())

    @router.post("/api/unprivileged_tools/build")
    def build(
        self,
        payload: DynamicUnprivilegedToolCreatePayload,
        history_id: DecodedDatabaseIdField,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ):
        history = trans.app.history_manager.get_owned(history_id, trans.user)
        tool = tool_payload_to_tool(trans.app, payload.representation.model_dump(by_alias=True))
        if tool:
            return tool.to_json(trans=trans, history=history or trans.history)

    @router.post("/api/unprivileged_tools/runtime_model")
    def runtime_model(self, payload: DynamicUnprivilegedToolCreatePayload, user: User = DependsOnUser):
        self.dynamic_tools_manager.ensure_can_use_unprivileged_tool(user)
        represention = payload.representation.model_dump(by_alias=True)
        tool_source = YamlToolSource(root_dict=represention)
        input_bundle = input_models_for_tool_source(tool_source)
        return cwl_runtime_model(input_bundle)

    @router.delete("/api/unprivileged_tools/{uuid}")
    def delete(self, uuid: str, user: User = DependsOnUser):
        """
        DELETE /api/unprivileged_tools/{encoded_dynamic_tool_id|tool_uuid}

        Deactivate the specified dynamic tool. Deactivated tools will not
        be loaded into the toolbox.
        """
        dynamic_tool = self.dynamic_tools_manager.get_unprivileged_tool_by_uuid(user, uuid)
        if not dynamic_tool:
            raise ObjectNotFound()
        self.dynamic_tools_manager.deactivate_unprivileged_tool(user, dynamic_tool)


@router.cbv
class DynamicToolApi:
    dynamic_tools_manager: DynamicToolManager = depends(DynamicToolManager)

    @router.get("/api/dynamic_tools", public=True)
    def index(self):
        return [t.to_dict() for t in self.dynamic_tools_manager.list_tools()]

    @router.get("/api/dynamic_tools/{dynamic_tool_id}", public=True)
    def show(self, dynamic_tool_id: DatabaseIdOrUUID | str):
        dynamic_tool = self.dynamic_tools_manager.get_tool_by_id_or_uuid(dynamic_tool_id)
        if dynamic_tool is None:
            raise ObjectNotFound()
        return dynamic_tool.to_dict()

    @router.post("/api/dynamic_tools", require_admin=True)
    def create(self, payload: DynamicToolPayload):
        try:
            dynamic_tool = self.dynamic_tools_manager.create_tool(payload)
        except MessageException:
            raise
        except Exception as e:
            raise RequestParameterInvalidException(str(e))
        return dynamic_tool.to_dict()

    @router.delete("/api/dynamic_tools/{dynamic_tool_id}", require_admin=True)
    def delete(self, dynamic_tool_id: DatabaseIdOrUUID) -> dict[str, Any]:
        """
        DELETE /api/dynamic_tools/{encoded_dynamic_tool_id|tool_uuid}

        Deactivate the specified dynamic tool. Deactivated tools will not
        be loaded into the toolbox.
        """
        dynamic_tool = self.dynamic_tools_manager.get_tool_by_id_or_uuid(dynamic_tool_id)
        if dynamic_tool is None:
            raise ObjectNotFound()
        updated_dynamic_tool = self.dynamic_tools_manager.deactivate(dynamic_tool)
        return updated_dynamic_tool.to_dict()
