"""
API operations on Group objects.
"""
import logging
from typing import (
    Any,
    Dict,
)

from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.groups import GroupsManager
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.web import (
    expose_api,
    require_admin,
)
from . import (
    BaseGalaxyAPIController,
    depends,
)

log = logging.getLogger(__name__)


class GroupAPIController(BaseGalaxyAPIController):
    manager = depends(GroupsManager)

    @expose_api
    @require_admin
    def index(self, trans: ProvidesAppContext, **kwd):
        """
        GET /api/groups
        Displays a collection (list) of groups.
        """
        return self.manager.index(trans)

    @expose_api
    @require_admin
    def create(self, trans: ProvidesAppContext, payload: Dict[str, Any], **kwd):
        """
        POST /api/groups
        Creates a new group.
        """
        return self.manager.create(trans, payload)

    @expose_api
    @require_admin
    def show(self, trans: ProvidesAppContext, id: EncodedDatabaseIdField, **kwd):
        """
        GET /api/groups/{encoded_group_id}
        Displays information about a group.
        """
        return self.manager.show(trans, id)

    @expose_api
    @require_admin
    def update(self, trans: ProvidesAppContext, id: EncodedDatabaseIdField, payload: Dict[str, Any], **kwd):
        """
        PUT /api/groups/{encoded_group_id}
        Modifies a group.
        """
        self.manager.update(trans, id, payload)
