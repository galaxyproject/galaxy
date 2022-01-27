"""
API operations on Role objects.
"""
import logging

from fastapi import Body

from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.roles import RoleManager
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    RoleDefinitionModel,
    RoleListModelResponse,
    RoleModelResponse,
)
from galaxy.webapps.base.controller import url_for
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)


# Empty paths (e.g. /api/roles) only work if a prefix is defined right here.
# https://github.com/tiangolo/fastapi/pull/415/files
router = Router(tags=["roles"])


def role_to_model(trans, role):
    item = role.to_dict(view="element", value_mapper={"id": trans.security.encode_id})
    role_id = trans.security.encode_id(role.id)
    item["url"] = url_for("role", id=role_id)
    return RoleModelResponse(**item)


@router.cbv
class FastAPIRoles:
    role_manager: RoleManager = depends(RoleManager)

    @router.get("/api/roles")
    def index(self, trans: ProvidesUserContext = DependsOnTrans) -> RoleListModelResponse:
        roles = self.role_manager.list_displayable_roles(trans)
        return RoleListModelResponse(__root__=[role_to_model(trans, r) for r in roles])

    @router.get("/api/roles/{role_id}")
    def show(self, role_id: DecodedDatabaseIdField, trans: ProvidesUserContext = DependsOnTrans) -> RoleModelResponse:
        role = self.role_manager.get(trans, role_id)
        return role_to_model(trans, role)

    @router.post("/api/roles", require_admin=True)
    def create(
        self, trans: ProvidesUserContext = DependsOnTrans, role_definition_model: RoleDefinitionModel = Body(...)
    ) -> RoleModelResponse:
        role = self.role_manager.create_role(trans, role_definition_model)
        return role_to_model(trans, role)
