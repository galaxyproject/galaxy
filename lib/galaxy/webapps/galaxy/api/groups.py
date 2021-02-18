"""
API operations on Group objects.
"""
import logging

from galaxy.managers.groups import GroupsManager
from galaxy.web import (
    expose_api,
    require_admin,
)
from galaxy.webapps.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class GroupAPIController(BaseAPIController):

    def __init__(self, app):
        super().__init__(app)
        self.manager = GroupsManager()

    @expose_api
    @require_admin
    def index(self, trans, **kwd):
        """
        GET /api/groups
        Displays a collection (list) of groups.
        """
        return self.manager.index(trans)

    @expose_api
    @require_admin
    def create(self, trans, payload, **kwd):
        """
        POST /api/groups
        Creates a new group.
        """
        return self.manager.create(trans, payload)

    @expose_api
    @require_admin
    def show(self, trans, id, **kwd):
        """
        GET /api/groups/{encoded_group_id}
        Displays information about a group.
        """
        return self.manager.show(trans, id)

    @expose_api
    @require_admin
    def update(self, trans, id, payload, **kwd):
        """
        PUT /api/groups/{encoded_group_id}
        Modifies a group.
        """
        self.manager.update(trans, id, payload)
