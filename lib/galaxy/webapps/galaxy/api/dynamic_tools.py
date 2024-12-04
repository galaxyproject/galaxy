import logging
from typing import (
    Literal,
    Optional,
)

from pydantic.main import BaseModel

from galaxy.exceptions import ObjectNotFound
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.tools import DynamicToolManager
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.tool_util.models import UserToolSource
from . import (
    depends,
    DependsOnTrans,
    Router,
)


class DynamicToolCreatePayload(BaseModel):
    allow_load: bool = True
    uuid: Optional[str] = None
    src: Literal["representation", "path"] = "representation"
    representation: UserToolSource
    active: Optional[bool] = None
    hidden: Optional[bool] = None
    path: Optional[str] = None
    tool_directory: Optional[str] = None


log = logging.getLogger(__name__)

router = Router(tags=["dynamic_tools"])


@router.cbv
class DynamicToolApi:
    dynamic_tools_manager: DynamicToolManager = depends(DynamicToolManager)

    @router.get("/api/dynamic_tools")
    def index(self):
        return [t.to_dict() for t in self.dynamic_tools_manager.list_tools()]

    @router.get("/api/dynamic_tools/{dynamic_tool_id}")
    def show(self, dynamic_tool_id: DecodedDatabaseIdField):
        dynamic_tool = self.dynamic_tools_manager.get_tool_by_id(dynamic_tool_id)
        if dynamic_tool is None:
            raise ObjectNotFound()
        return dynamic_tool.to_dict()

    @router.post("/api/dynamic_tools", require_admin=True)
    def create(self, payload: DynamicToolCreatePayload, trans: ProvidesUserContext = DependsOnTrans):
        dynamic_tool = self.dynamic_tools_manager.create_tool(trans, payload, allow_load=payload.allow_load)
        return dynamic_tool.to_dict()

    @router.delete("/api/dynamic_tools/{dynamic_tool_id}")
    def delete(self, trans, dynamic_tool_id: DecodedDatabaseIdField, **kwd):
        """
        DELETE /api/dynamic_tools/{encoded_dynamic_tool_id|tool_uuid}

        Deactivate the specified dynamic tool. Deactivated tools will not
        be loaded into the toolbox.
        """
        dynamic_tool = dynamic_tool = self.dynamic_tools_manager.get_tool_by_id(dynamic_tool_id)
        updated_dynamic_tool = self.dynamic_tools_manager.deactivate(dynamic_tool)
        return updated_dynamic_tool.to_dict()
