"""
API operations on Role objects.
"""

import logging
from typing import Optional

from fastapi import (
    Body,
    Query,
)

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

SearchRolesQueryParam: Optional[str] = Query(
    default=None,
    title="Search filter",
    description="Search by role name or user email (for private roles).",
)
LimitRolesQueryParam: Optional[int] = Query(
    default=None,
    ge=1,
    title="Limit",
    description="The maximum number of roles to return.",
)
OffsetRolesQueryParam: Optional[int] = Query(
    default=0,
    ge=0,
    title="Offset",
    description="Number of roles to skip.",
)


# Empty paths (e.g. /api/roles) only work if a prefix is defined right here.
# https://github.com/tiangolo/fastapi/pull/415/files
router = Router(tags=["roles"])


@router.cbv
class FastAPIRoles:
    service: RolesService = depends(RolesService)

    @router.get("/api/roles")
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        search: Optional[str] = SearchRolesQueryParam,
        limit: Optional[int] = LimitRolesQueryParam,
        offset: Optional[int] = OffsetRolesQueryParam,
    ) -> RoleListResponse:
        return self.service.get_index(trans=trans, search=search, limit=limit, offset=offset)

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
