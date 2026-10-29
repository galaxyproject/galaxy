"""
API operations on Role objects.
"""

import logging

from fastapi import (
    Body,
    Query,
)

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.schema import (
    GroupModelListResponse,
    RoleDefinitionModel,
    RoleListResponse,
    RoleModelResponse,
    RoleUpdatePayload,
    RoleUserListResponse,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.api.common import RoleIDPathParam
from galaxy.webapps.galaxy.services.roles import RolesService

log = logging.getLogger(__name__)

SearchRolesQueryParam: str | None = Query(
    default=None,
    title="Search filter",
    description="Search by role name or user email (for private roles).",
)
LimitRolesQueryParam: int | None = Query(
    default=None,
    ge=1,
    title="Limit",
    description="The maximum number of roles to return.",
)
OffsetRolesQueryParam: int | None = Query(
    default=0,
    ge=0,
    title="Offset",
    description="Number of roles to skip.",
)
ExcludePrivateRolesQueryParam: bool = Query(
    default=False,
    title="Exclude private roles",
    description="Leave out the private role of each user.",
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
        search: str | None = SearchRolesQueryParam,
        limit: int | None = LimitRolesQueryParam,
        offset: int | None = OffsetRolesQueryParam,
        exclude_private: bool = ExcludePrivateRolesQueryParam,
    ) -> RoleListResponse:
        return self.service.get_index(
            trans=trans, search=search, limit=limit, offset=offset, exclude_private=exclude_private
        )

    @router.get("/api/roles/{id}")
    def show(self, id: RoleIDPathParam, trans: ProvidesUserContext = DependsOnTrans) -> RoleModelResponse:
        return self.service.show(trans, id)

    @router.post("/api/roles", require_admin=True)
    def create(
        self, trans: ProvidesUserContext = DependsOnTrans, role_definition_model: RoleDefinitionModel = Body(...)
    ) -> RoleModelResponse:
        return self.service.create(trans, role_definition_model)

    @router.put("/api/roles/{id}", require_admin=True, summary="Update a role's name, description, users and groups")
    def update(
        self,
        id: RoleIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: RoleUpdatePayload = Body(...),
    ) -> RoleModelResponse:
        return self.service.update(trans, id, payload)

    @router.get("/api/roles/{id}/users", require_admin=True, summary="List the users associated with a role")
    def users(self, id: RoleIDPathParam, trans: ProvidesUserContext = DependsOnTrans) -> RoleUserListResponse:
        return self.service.get_users(trans, id)

    @router.get("/api/roles/{id}/groups", require_admin=True, summary="List the groups associated with a role")
    def groups(self, id: RoleIDPathParam, trans: ProvidesUserContext = DependsOnTrans) -> GroupModelListResponse:
        return self.service.get_groups(trans, id)

    @router.delete("/api/roles/{id}", require_admin=True)
    def delete(self, id: RoleIDPathParam, trans: ProvidesUserContext = DependsOnTrans) -> RoleModelResponse:
        return self.service.delete(trans, id)

    @router.post("/api/roles/{id}/purge", require_admin=True)
    def purge(self, id: RoleIDPathParam, trans: ProvidesUserContext = DependsOnTrans) -> RoleModelResponse:
        return self.service.purge(trans, id)

    @router.post("/api/roles/{id}/undelete", require_admin=True)
    def undelete(self, id: RoleIDPathParam, trans: ProvidesUserContext = DependsOnTrans) -> RoleModelResponse:
        return self.service.undelete(trans, id)
