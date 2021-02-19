"""
API operations on Group objects.
"""
import logging

from galaxy.managers.group_users import GroupUsersManager
from galaxy.web import (
    expose_api,
    require_admin,
)
from galaxy.webapps.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class GroupUsersAPIController(BaseAPIController):

    def __init__(self, app):
        super().__init__(app)
        self.manager = GroupUsersManager(app)

    @require_admin
    @expose_api
    def index(self, trans, group_id, **kwd):
        """
        GET /api/groups/{encoded_group_id}/users
        Displays a collection (list) of groups.
        """
        return self.manager.index(trans, group_id)

    @require_admin
    @expose_api
    def show(self, trans, id, group_id, **kwd):
        """
        GET /api/groups/{encoded_group_id}/users/{encoded_user_id}
        Displays information about a group user.
        """
        return self.manager.show(trans, id, group_id)

    @require_admin
    @expose_api
    def update(self, trans, id, group_id, **kwd):
        """
        PUT /api/groups/{encoded_group_id}/users/{encoded_user_id}
        Adds a user to a group
        """
        return self.manager.update(trans, id, group_id)

    @require_admin
    @expose_api
    def delete(self, trans, id, group_id, **kwd):
        """
        DELETE /api/groups/{encoded_group_id}/users/{encoded_user_id}
        Removes a user from a group
        """
        return self.manager.delete(trans, id, group_id)
