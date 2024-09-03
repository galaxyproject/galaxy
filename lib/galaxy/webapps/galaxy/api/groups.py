"""
API operations on Group objects.
"""

import logging

from fastapi import (
    Body,
    Path,
)
from typing_extensions import Annotated

from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.groups import GroupsManager
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.groups import (
    GroupCreatePayload,
    GroupListResponse,
    GroupResponse,
    GroupUpdatePayload,
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
        response_model_exclude_unset=True,
    )
    def index(
        self,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> GroupListResponse:
        return self.manager.index(trans)

    @router.post(
        "/api/groups",
        summary="Creates a new group.",
        require_admin=True,
        response_model_exclude_unset=True,
    )
    def create(
        self,
        payload: Annotated[GroupCreatePayload, Body(...)],
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> GroupListResponse:
        return self.manager.create(trans, payload)

    @router.get(
        "/api/groups/{group_id}",
        summary="Displays information about a group.",
        require_admin=True,
        name="show_group",
    )
    def show(
        self,
        group_id: Annotated[DecodedDatabaseIdField, Path(...)],
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> GroupResponse:
        return self.manager.show(trans, group_id)

    @router.put(
        "/api/groups/{group_id}",
        summary="Modifies a group.",
        require_admin=True,
        response_model_exclude_unset=True,
    )
    def update(
        self,
        group_id: Annotated[DecodedDatabaseIdField, Path(...)],
        payload: Annotated[GroupUpdatePayload, Body(...)],
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> GroupResponse:
        return self.manager.update(trans, group_id, payload)

    @router.delete("/api/groups/{group_id}", require_admin=True)
    def delete(self, group_id: DecodedDatabaseIdField, trans: ProvidesAppContext = DependsOnTrans):
        self.manager.delete(trans, group_id)

    @router.post("/api/groups/{group_id}/purge", require_admin=True)
    def purge(self, group_id: DecodedDatabaseIdField, trans: ProvidesAppContext = DependsOnTrans):
        self.manager.purge(trans, group_id)

    @router.post("/api/groups/{group_id}/undelete", require_admin=True)
    def undelete(self, group_id: DecodedDatabaseIdField, trans: ProvidesAppContext = DependsOnTrans):
        self.manager.undelete(trans, group_id)
