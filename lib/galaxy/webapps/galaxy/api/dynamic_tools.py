import logging
from typing import Union

from galaxy.exceptions import ObjectNotFound
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.tools import DynamicToolManager
from galaxy.model import User
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.tools import (
    DynamicToolPayload,
    DynamicUnprivilegedToolCreatePayload,
)
from . import (
    depends,
    DependsOnTrans,
    DependsOnUser,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["dynamic_tools"])

DatabaseIdOrUUID = Union[DecodedDatabaseIdField, str]


@router.cbv
class UnprivilegedToolsApi:
    # Almost identical to dynamic tools api, but operates with tool ids
    # and is scoped to to individual user and never adds to global toolbox
    dynamic_tools_manager: DynamicToolManager = depends(DynamicToolManager)

    @router.get("/api/unprivileged_tools")
    def index(self, active: bool = True, trans: ProvidesUserContext = DependsOnTrans):
        if not trans.user:
            return []
        return [t.to_dict() for t in self.dynamic_tools_manager.list_unprivileged_tools(trans.user, active=active)]

    @router.get("/api/unprivileged_tools/{tool_id}")
    def show(self, tool_id: str, user: User = DependsOnUser):
        dynamic_tool = self.dynamic_tools_manager.get_unprivileged_tool_by_tool_id(user, tool_id)
        if dynamic_tool is None:
            raise ObjectNotFound()
        return dynamic_tool.to_dict()

    @router.post("/api/unprivileged_tools")
    def create(self, payload: DynamicUnprivilegedToolCreatePayload, user: User = DependsOnUser):
        dynamic_tool = self.dynamic_tools_manager.create_unprivileged_tool(
            user,
            payload,
        )
        return dynamic_tool.to_dict()

    @router.delete("/api/dynamic_tools/{tool_id}")
    def delete(self, tool_id: str, user: User = DependsOnUser):
        """
        DELETE /api/dynamic_tools/{encoded_dynamic_tool_id|tool_uuid}

        Deactivate the specified dynamic tool. Deactivated tools will not
        be loaded into the toolbox.
        """
        dynamic_tool = self.dynamic_tools_manager.get_unprivileged_tool_by_tool_id(user, tool_id)
        if not dynamic_tool:
            raise ObjectNotFound()
        updated_dynamic_tool = self.dynamic_tools_manager.deactivate_unprivileged_tool(user, dynamic_tool)
        return updated_dynamic_tool.to_dict()


@router.cbv
class DynamicToolApi:
    dynamic_tools_manager: DynamicToolManager = depends(DynamicToolManager)

    @router.get("/api/dynamic_tools")
    def index(self):
        return [t.to_dict() for t in self.dynamic_tools_manager.list_tools()]

    @router.get("/api/dynamic_tools/{dynamic_tool_id}")
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
