"""
API operations on Role objects.
"""

import logging

from fastapi import Body

from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.roles import RoleManager
from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    Security,
)
from galaxy.schema.schema import (
    RoleDefinitionModel,
    RoleListResponse,
    RoleModelResponse,
)
from galaxy.webapps.base.controller import url_for
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)


# Empty paths (e.g. /api/roles) only work if a prefix is defined right here.
# https://github.com/tiangolo/fastapi/pull/415/files
router = Router(tags=["roles"])


def role_to_model(role):
    item = role.to_dict(view="element")
    role_id = Security.security.encode_id(role.id)
    item["url"] = url_for("role", id=role_id)
    return RoleModelResponse(**item)


@router.cbv
class FastAPIRoles:
    role_manager: RoleManager = depends(RoleManager)

    @router.get("/api/roles")
    def index(self, trans: ProvidesUserContext = DependsOnTrans) -> RoleListResponse:
        roles = self.role_manager.list_displayable_roles(trans)
        return RoleListResponse(root=[role_to_model(r) for r in roles])

    @router.get("/api/roles/{id}")
    def show(self, id: DecodedDatabaseIdField, trans: ProvidesUserContext = DependsOnTrans) -> RoleModelResponse:
        role = self.role_manager.get(trans, id)
        return role_to_model(role)

    @router.post("/api/roles", require_admin=True)
    def create(
        self, trans: ProvidesUserContext = DependsOnTrans, role_definition_model: RoleDefinitionModel = Body(...)
    ) -> RoleModelResponse:
        role = self.role_manager.create_role(trans, role_definition_model)
        return role_to_model(role)

    @router.delete("/api/roles/{id}", require_admin=True)
    def delete(self, id: DecodedDatabaseIdField, trans: ProvidesUserContext = DependsOnTrans) -> RoleModelResponse:
        role = self.role_manager.get(trans, id)
        role = self.role_manager.delete(trans, role)
        return role_to_model(role)

    @router.post("/api/roles/{id}/purge", require_admin=True)
    def purge(self, id: DecodedDatabaseIdField, trans: ProvidesUserContext = DependsOnTrans) -> RoleModelResponse:
        role = self.role_manager.get(trans, id)
        role = self.role_manager.purge(trans, role)
        return role_to_model(role)

    @router.post("/api/roles/{id}/undelete", require_admin=True)
    def undelete(self, id: DecodedDatabaseIdField, trans: ProvidesUserContext = DependsOnTrans) -> RoleModelResponse:
        role = self.role_manager.get(trans, id)
        role = self.role_manager.undelete(trans, role)
        return role_to_model(role)
