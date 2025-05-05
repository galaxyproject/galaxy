"""
API operations on Group objects.
"""

import logging
from typing import Optional

from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.group_roles import GroupRolesManager
from galaxy.model.db.role import get_private_role_user_emails_dict
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


def group_role_to_model(trans, group_id: int, role, displayed_name: Optional[str] = None) -> GroupRoleResponse:
    encoded_group_id = Security.security.encode_id(group_id)
    encoded_role_id = Security.security.encode_id(role.id)
    url = trans.url_builder("group_role", group_id=encoded_group_id, role_id=encoded_role_id)
    displayed_name = displayed_name or role.name
    return GroupRoleResponse(id=role.id, name=displayed_name, url=url)


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
        private_role_emails = get_private_role_user_emails_dict(trans.sa_session)
        data = []
        for group in group_roles:
            role = group.role
            displayed_name = private_role_emails.get(role.id, role.name)
            data.append(group_role_to_model(trans, group_id, role, displayed_name))
        return GroupRoleListResponse(root=data)

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
