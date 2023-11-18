"""
API operations on Group objects.
"""
import logging

from fastapi import (
    Body,
    Path,
)

from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.groups import GroupsManager
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.groups import (
    GroupCreatePayload,
    GroupIndexListResponse,
    GroupShowResponse,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["groups"])


@router.cbv
class FastAPIGroups:
    manager: GroupsManager = depends(GroupsManager)

    @router.get(
        "/api/groups",
        summary="Displays a collection (list) of groups.",
        require_admin=True,
    )
    def index(
        self,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> GroupIndexListResponse:
        """GET /api/groups - Displays a collection (list) of groups."""
        return self.manager.index(trans)

    @router.post(
        "/api/groups",
        summary="Creates a new group.",
        require_admin=True,
    )
    def create(
        self,
        trans: ProvidesAppContext = DependsOnTrans,
        payload: GroupCreatePayload = Body(),
    ) -> GroupIndexListResponse:
        """POST /api/groups - Creates a new group."""
        return self.manager.create(trans, payload)

    @router.get(
        "/api/groups/{encoded_group_id}",
        summary="Displays information about a group.",
        require_admin=True,
    )
    def show(
        self,
        trans: ProvidesAppContext = DependsOnTrans,
        encoded_group_id: EncodedDatabaseIdField = Path(),
    ) -> GroupShowResponse:
        """GET /api/groups/{encoded_group_id} - Displays information about a group."""
        group_id = EncodedDatabaseIdField.decode(encoded_group_id)
        return self.manager.show(trans, group_id)

    @router.put(
        "/api/groups/{encoded_group_id}",
        summary="Modifies a group.",
        require_admin=True,
    )
    def update(
        self,
        trans: ProvidesAppContext = DependsOnTrans,
        encoded_group_id: EncodedDatabaseIdField = Path(),
        payload: GroupCreatePayload = Body(),
    ):
        """PUT /api/groups/{encoded_group_id} - Modifies a group."""
        group_id = EncodedDatabaseIdField.decode(encoded_group_id)
        self.manager.update(trans, group_id, payload)
