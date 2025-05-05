"""
API operations on Role objects.
"""

import logging

from fastapi import Body

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.schema import (
    RoleDefinitionModel,
    RoleListResponse,
    RoleModelResponse,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.api.common import RoleIDPathParam
from galaxy.webapps.galaxy.services.roles import RolesService

log = logging.getLogger(__name__)


# Empty paths (e.g. /api/roles) only work if a prefix is defined right here.
# https://github.com/tiangolo/fastapi/pull/415/files
router = Router(tags=["roles"])


@router.cbv
class FastAPIRoles:
    service: RolesService = depends(RolesService)

    @router.get("/api/roles")
    def index(self, trans: ProvidesUserContext = DependsOnTrans) -> RoleListResponse:
        return self.service.get_index(trans=trans)

    @router.get("/api/roles/{id}")
    def show(self, id: RoleIDPathParam, trans: ProvidesUserContext = DependsOnTrans) -> RoleModelResponse:
        return self.service.show(trans, id)

    @router.post("/api/roles", require_admin=True)
    def create(
        self, trans: ProvidesUserContext = DependsOnTrans, role_definition_model: RoleDefinitionModel = Body(...)
    ) -> RoleModelResponse:
        return self.service.create(trans, role_definition_model)

    @router.delete("/api/roles/{id}", require_admin=True)
    def delete(self, id: RoleIDPathParam, trans: ProvidesUserContext = DependsOnTrans) -> RoleModelResponse:
        return self.service.delete(trans, id)

    @router.post("/api/roles/{id}/purge", require_admin=True)
    def purge(self, id: RoleIDPathParam, trans: ProvidesUserContext = DependsOnTrans) -> RoleModelResponse:
        return self.service.purge(trans, id)

    @router.post("/api/roles/{id}/undelete", require_admin=True)
    def undelete(self, id: RoleIDPathParam, trans: ProvidesUserContext = DependsOnTrans) -> RoleModelResponse:
        return self.service.undelete(trans, id)
