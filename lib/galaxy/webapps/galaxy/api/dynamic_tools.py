import logging
from datetime import datetime
from typing import (
    List,
    Optional,
    Union,
)

from pydantic import BaseModel

from galaxy.exceptions import ObjectNotFound
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
from galaxy.tool_util_models import UserToolSource
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

DatabaseIdOrUUID = Union[DecodedDatabaseIdField, str]


class UnprivilegedToolResponse(BaseModel):
    id: EncodedDatabaseIdField
    uuid: str
    active: bool
    hidden: bool
    tool_id: Optional[str]
    tool_format: Optional[str]
    create_time: datetime
    representation: UserToolSource


@router.cbv
class UnprivilegedToolsApi:
    # Almost identical to dynamic tools api, but operates with tool ids
    # and is scoped to to individual user and never adds to global toolbox
    dynamic_tools_manager: DynamicToolManager = depends(DynamicToolManager)

    @router.get("/api/unprivileged_tools", response_model_exclude_defaults=True)
    def index(self, active: bool = True, trans: ProvidesUserContext = DependsOnTrans) -> List[UnprivilegedToolResponse]:
        if not trans.user:
            return []
        return [t.to_dict() for t in self.dynamic_tools_manager.list_unprivileged_tools(trans.user, active=active)]

    @router.get("/api/unprivileged_tools/{uuid}", response_model_exclude_defaults=True)
    def show(self, uuid: str, user: User = DependsOnUser) -> UnprivilegedToolResponse:
        dynamic_tool = self.dynamic_tools_manager.get_unprivileged_tool_by_uuid(user, uuid)
        if dynamic_tool is None:
            raise ObjectNotFound()
        return UnprivilegedToolResponse(**dynamic_tool.to_dict())

    @router.post("/api/unprivileged_tools", response_model_exclude_defaults=True)
    def create(
        self, payload: DynamicUnprivilegedToolCreatePayload, user: User = DependsOnUser
    ) -> UnprivilegedToolResponse:
        dynamic_tool = self.dynamic_tools_manager.create_unprivileged_tool(
            user,
            payload,
        )
        return UnprivilegedToolResponse(**dynamic_tool.to_dict())

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
    def show(self, dynamic_tool_id: Union[DatabaseIdOrUUID, str]):
        dynamic_tool = self.dynamic_tools_manager.get_tool_by_id_or_uuid(dynamic_tool_id)
        if dynamic_tool is None:
            raise ObjectNotFound()
        return dynamic_tool.to_dict()

    @router.post("/api/dynamic_tools", require_admin=True)
    def create(self, payload: DynamicToolPayload, trans: ProvidesUserContext = DependsOnTrans):
        dynamic_tool = self.dynamic_tools_manager.create_tool(trans, payload, allow_load=payload.allow_load)
        return dynamic_tool.to_dict()

    @router.delete("/api/dynamic_tools/{dynamic_tool_id}", require_admin=True)
    def delete(self, dynamic_tool_id: DatabaseIdOrUUID):
        """
        DELETE /api/dynamic_tools/{encoded_dynamic_tool_id|tool_uuid}

        Deactivate the specified dynamic tool. Deactivated tools will not
        be loaded into the toolbox.
        """
        dynamic_tool = dynamic_tool = self.dynamic_tools_manager.get_tool_by_id_or_uuid(dynamic_tool_id)
        updated_dynamic_tool = self.dynamic_tools_manager.deactivate(dynamic_tool)
        return updated_dynamic_tool.to_dict()
