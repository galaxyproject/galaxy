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
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    GroupDefinitionModel,
    GroupUpdateModel,
)
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
    manager: GroupsManager = depends(GroupsManager)

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
        return self.manager.create(trans, GroupDefinitionModel(**payload))

    @expose_api
    @require_admin
    def show(self, trans: ProvidesAppContext, id: DecodedDatabaseIdField, **kwd):
        """
        GET /api/groups/{encoded_group_id}
        Displays information about a group.
        """
        id = self.decode_id(id)
        return self.manager.show(trans, id)

    @expose_api
    @require_admin
    def update(self, trans: ProvidesAppContext, id: DecodedDatabaseIdField, payload: Dict[str, Any], **kwd):
        """
        PUT /api/groups/{encoded_group_id}
        Modifies a group.
        """
        id = self.decode_id(id)
        self.manager.update(trans, id, GroupUpdateModel(**payload))
