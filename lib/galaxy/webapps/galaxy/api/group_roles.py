"""
API operations on Group objects.
"""

import logging

from fastapi import Path

from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.group_roles import GroupRolesManager
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import GroupRoleListModel, GroupRoleModel
from galaxy.web import (
    expose_api,
    require_admin,
)
from . import (
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    Router
)


log = logging.getLogger(__name__)

router = Router(tags=['group_roles'])

GroupIDParam: EncodedDatabaseIdField = Path(
    ...,
    title='GroupID',
    description='The ID of the group'
)

RoleIDParam: EncodedDatabaseIdField = Path(
    ...,
    title='RoleID',
    description='The ID of the role'
)


def group_role_to_model(trans, encoded_group_id, role):
    encoded_role_id = trans.security.encode_id(role.id)
    url = trans.url_builder('group_role', group_id=encoded_group_id, id=encoded_role_id)
    return GroupRoleModel(
        id=encoded_role_id,
        name=role.name,
        url=url
    )


@router.cbv
class FastAPIGroupRoles:
    manager: GroupRolesManager = depends(GroupRolesManager)

    @router.get('/api/groups/{group_id}/roles',
                require_admin=True,
                summary='Displays a collection (list) of groups.')
    def index(self, trans: ProvidesAppContext = DependsOnTrans,
              group_id: EncodedDatabaseIdField = GroupIDParam) -> GroupRoleListModel:
        group_roles = self.manager.index(trans, group_id)
        return GroupRoleListModel(__root__=[group_role_to_model(trans, group_id, gr.role) for gr in group_roles])

    @router.get('/api/groups/{group_id}/roles/{id}',
                name="group_role",
                require_admin=True,
                summary='Displays information about a group role.')
    def show(self, trans: ProvidesAppContext = DependsOnTrans,
             group_id: EncodedDatabaseIdField = GroupIDParam,
             id: EncodedDatabaseIdField = RoleIDParam) -> GroupRoleModel:
        role = self.manager.show(trans, id, group_id)
        return group_role_to_model(trans, group_id, role)

    @router.put('/api/groups/{group_id}/roles/{role_id}',
                require_admin=True,
                summary='Adds a role to a group')
    def update(self, trans: ProvidesAppContext = DependsOnTrans,
               group_id: EncodedDatabaseIdField = GroupIDParam,
               role_id: EncodedDatabaseIdField = RoleIDParam) -> GroupRoleModel:
        role = self.manager.update(trans, role_id, group_id)
        return group_role_to_model(trans, group_id, role)

    @router.delete('/api/groups/{group_id}/roles/{role_id}',
                   require_admin=True,
                   summary='Removes a role from a group')
    def delete(self, trans: ProvidesAppContext = DependsOnTrans,
               group_id: EncodedDatabaseIdField = GroupIDParam,
               role_id: EncodedDatabaseIdField = RoleIDParam) -> GroupRoleModel:
        role = self.manager.delete(trans, role_id, group_id)
        return group_role_to_model(trans, group_id, role)


class GroupRolesAPIController(BaseGalaxyAPIController):
    manager = depends(GroupRolesManager)

    @require_admin
    @expose_api
    def index(self, trans: ProvidesAppContext, group_id: EncodedDatabaseIdField, **kwd):
        """
        GET /api/groups/{encoded_group_id}/roles
        Displays a collection (list) of groups.
        """
        group_roles = self.manager.index(trans, group_id)
        return GroupRoleListModel(__root__=[group_role_to_model(trans, group_id, gr.role) for gr in group_roles])

    @require_admin
    @expose_api
    def show(self, trans: ProvidesAppContext, id: EncodedDatabaseIdField, group_id: EncodedDatabaseIdField, **kwd):
        """
        GET /api/groups/{encoded_group_id}/roles/{encoded_role_id}
        Displays information about a group role.
        """
        role = self.manager.show(trans, id, group_id)
        return group_role_to_model(trans, group_id, role)

    @require_admin
    @expose_api
    def update(self, trans: ProvidesAppContext, id: EncodedDatabaseIdField, group_id: EncodedDatabaseIdField, **kwd):
        """
        PUT /api/groups/{encoded_group_id}/roles/{encoded_role_id}
        Adds a role to a group
        """
        role = self.manager.update(trans, id, group_id)
        return group_role_to_model(trans, group_id, role)

    @require_admin
    @expose_api
    def delete(self, trans: ProvidesAppContext, id: EncodedDatabaseIdField, group_id: EncodedDatabaseIdField, **kwd):
        """
        DELETE /api/groups/{encoded_group_id}/roles/{encoded_role_id}
        Removes a role from a group
        """
        role = self.manager.delete(trans, id, group_id)
        return group_role_to_model(trans, group_id, role)
