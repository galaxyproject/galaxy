"""
API operations on Group objects.
"""

import logging

from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.group_roles import GroupRolesManager
from galaxy.schema.fields import Security
from galaxy.schema.schema import (
    GroupRoleListResponse,
    GroupRoleResponse,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.api.common import (
    GroupIDPathParam,
    RoleIDPathParam,
)

log = logging.getLogger(__name__)

router = Router(tags=["group_roles"])


def group_role_to_model(trans, group_id: int, role) -> GroupRoleResponse:
    encoded_group_id = Security.security.encode_id(group_id)
    encoded_role_id = Security.security.encode_id(role.id)
    url = trans.url_builder("group_role", group_id=encoded_group_id, role_id=encoded_role_id)
    return GroupRoleResponse(id=role.id, name=role.name, url=url)


@router.cbv
class FastAPIGroupRoles:
    manager: GroupRolesManager = depends(GroupRolesManager)

    @router.get(
        "/api/groups/{group_id}/roles",
        require_admin=True,
        summary="Displays a collection (list) of groups.",
        name="group_roles",
    )
    def index(
        self,
        group_id: GroupIDPathParam,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> GroupRoleListResponse:
        group_roles = self.manager.index(trans, group_id)
        return GroupRoleListResponse(root=[group_role_to_model(trans, group_id, gr.role) for gr in group_roles])

    @router.get(
        "/api/groups/{group_id}/roles/{role_id}",
        name="group_role",
        require_admin=True,
        summary="Displays information about a group role.",
    )
    def show(
        self,
        group_id: GroupIDPathParam,
        role_id: RoleIDPathParam,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> GroupRoleResponse:
        role = self.manager.show(trans, role_id, group_id)
        return group_role_to_model(trans, group_id, role)

    @router.put("/api/groups/{group_id}/roles/{role_id}", require_admin=True, summary="Adds a role to a group")
    def update(
        self,
        group_id: GroupIDPathParam,
        role_id: RoleIDPathParam,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> GroupRoleResponse:
        role = self.manager.update(trans, role_id, group_id)
        return group_role_to_model(trans, group_id, role)

    @router.delete("/api/groups/{group_id}/roles/{role_id}", require_admin=True, summary="Removes a role from a group")
    def delete(
        self,
        group_id: GroupIDPathParam,
        role_id: RoleIDPathParam,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> GroupRoleResponse:
        role = self.manager.delete(trans, role_id, group_id)
        return group_role_to_model(trans, group_id, role)
