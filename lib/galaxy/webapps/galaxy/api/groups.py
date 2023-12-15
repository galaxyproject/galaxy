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
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.groups import (
    GroupCreatePayload,
    GroupListResponse,
    GroupResponse,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["groups"])


class FastAPIGroups:
    @router.get(
        "/api/groups",
        summary="Displays a collection (list) of groups.",
        require_admin=True,
        response_model_exclude_unset=True,
    )
    def index(
        trans: ProvidesAppContext = DependsOnTrans,
        manager: GroupsManager = depends(GroupsManager),
    ) -> GroupListResponse:
        return manager.index(trans)

    @router.post(
        "/api/groups",
        summary="Creates a new group.",
        require_admin=True,
        response_model_exclude_unset=True,
    )
    def create(
        trans: ProvidesAppContext = DependsOnTrans,
        payload: GroupCreatePayload = Body(...),
        manager: GroupsManager = depends(GroupsManager),
    ) -> GroupListResponse:
        return manager.create(trans, payload)

    @router.get(
        "/api/groups/{group_id}",
        summary="Displays information about a group.",
        require_admin=True,
        name="show_group",
    )
    def show(
        trans: ProvidesAppContext = DependsOnTrans,
        group_id: DecodedDatabaseIdField = Path(...),
        manager: GroupsManager = depends(GroupsManager),
    ) -> GroupResponse:
        return manager.show(trans, group_id)

    @router.put(
        "/api/groups/{group_id}",
        summary="Modifies a group.",
        require_admin=True,
        response_model_exclude_unset=True,
    )
    def update(
        trans: ProvidesAppContext = DependsOnTrans,
        group_id: DecodedDatabaseIdField = Path(...),
        payload: GroupCreatePayload = Body(...),
        manager: GroupsManager = depends(GroupsManager),
    ) -> GroupResponse:
        return manager.update(trans, group_id, payload)

    @router.delete("/api/groups/{group_id}", require_admin=True)
    def delete(
        group_id: DecodedDatabaseIdField,
        trans: ProvidesAppContext = DependsOnTrans,
        manager: GroupsManager = depends(GroupsManager),
    ):
        manager.delete(trans, group_id)

    @router.post("/api/groups/{group_id}/purge", require_admin=True)
    def purge(
        group_id: DecodedDatabaseIdField,
        trans: ProvidesAppContext = DependsOnTrans,
        manager: GroupsManager = depends(GroupsManager),
    ):
        manager.purge(trans, group_id)

    @router.post("/api/groups/{group_id}/undelete", require_admin=True)
    def undelete(
        group_id: DecodedDatabaseIdField,
        trans: ProvidesAppContext = DependsOnTrans,
        manager: GroupsManager = depends(GroupsManager),
    ):
        manager.undelete(trans, group_id)
