"""
API operations on Group objects.
"""
import logging

from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.group_roles import GroupRolesManager
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.web import (
    expose_api,
    require_admin,
)
from . import BaseGalaxyAPIController, depends

log = logging.getLogger(__name__)


class GroupRolesAPIController(BaseGalaxyAPIController):
    manager = depends(GroupRolesManager)

    @require_admin
    @expose_api
    def index(self, trans: ProvidesAppContext, group_id: EncodedDatabaseIdField, **kwd):
        """
        GET /api/groups/{encoded_group_id}/roles
        Displays a collection (list) of groups.
        """
        return self.manager.index(trans, group_id)

    @require_admin
    @expose_api
    def show(self, trans: ProvidesAppContext, id: EncodedDatabaseIdField, group_id: EncodedDatabaseIdField, **kwd):
        """
        GET /api/groups/{encoded_group_id}/roles/{encoded_role_id}
        Displays information about a group role.
        """
        return self.manager.show(trans, id, group_id)

    @require_admin
    @expose_api
    def update(self, trans: ProvidesAppContext, id: EncodedDatabaseIdField, group_id: EncodedDatabaseIdField, **kwd):
        """
        PUT /api/groups/{encoded_group_id}/roles/{encoded_role_id}
        Adds a role to a group
        """
        return self.manager.update(trans, id, group_id)

    @require_admin
    @expose_api
    def delete(self, trans: ProvidesAppContext, id: EncodedDatabaseIdField, group_id: EncodedDatabaseIdField, **kwd):
        """
        DELETE /api/groups/{encoded_group_id}/roles/{encoded_role_id}
        Removes a role from a group
        """
        return self.manager.delete(trans, id, group_id)
