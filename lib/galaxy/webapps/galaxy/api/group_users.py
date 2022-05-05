"""
API operations on Group objects.
"""
import logging

from fastapi import Path

from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.group_users import GroupUsersManager
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import (
    GroupUserListModel,
    GroupUserModel,
)
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["group_users"])

GroupIDParam: EncodedDatabaseIdField = Path(..., title="GroupID", description="The ID of the group")

UserIDParam: EncodedDatabaseIdField = Path(..., title="UserID", description="The ID of the user")


def group_user_to_model(trans, encoded_group_id, user):
    encoded_user_id = trans.security.encode_id(user.id)
    url = trans.url_builder("group_user", group_id=encoded_group_id, id=encoded_user_id)
    return GroupUserModel(id=encoded_user_id, email=user.email, url=url)


@router.cbv
class FastAPIGroupUsers:
    manager: GroupUsersManager = depends(GroupUsersManager)

    @router.get("/api/groups/{group_id}/users", require_admin=True, summary="Displays a collection (list) of groups.")
    def index(
        self, trans: ProvidesAppContext = DependsOnTrans, group_id: EncodedDatabaseIdField = GroupIDParam
    ) -> GroupUserListModel:
        """
        GET /api/groups/{encoded_group_id}/users
        Displays a collection (list) of groups.
        """
        group_users = self.manager.index(trans, group_id)
        return GroupUserListModel(__root__=[group_user_to_model(trans, group_id, gr) for gr in group_users])

    @router.get(
        "/api/groups/{group_id}/user/{id}",
        alias="/api/groups/{group_id}/users/{id}",
        name="group_user",
        require_admin=True,
        summary="Displays information about a group user.",
    )
    def show(
        self,
        trans: ProvidesAppContext = DependsOnTrans,
        group_id: EncodedDatabaseIdField = GroupIDParam,
        id: EncodedDatabaseIdField = UserIDParam,
    ) -> GroupUserModel:
        """
        GET /api/groups/{encoded_group_id}/users/{encoded_user_id}
        Displays information about a group user.
        """
        user = self.manager.show(trans, id, group_id)
        return group_user_to_model(trans, group_id, user)

    @router.put(
        "/api/groups/{group_id}/users/{user_id}",
        alias="/api/groups/{group_id}/user/{user_id}",
        require_admin=True,
        summary="Adds a user to a group",
    )
    def update(
        self,
        trans: ProvidesAppContext = DependsOnTrans,
        group_id: EncodedDatabaseIdField = GroupIDParam,
        user_id: EncodedDatabaseIdField = UserIDParam,
    ) -> GroupUserModel:
        """
        PUT /api/groups/{encoded_group_id}/users/{encoded_user_id}
        Adds a user to a group
        """
        user = self.manager.update(trans, user_id, group_id)
        return group_user_to_model(trans, group_id, user)

    @router.delete(
        "/api/groups/{group_id}/user/{user_id}",
        alias="/api/groups/{group_id}/users/{user_id}",
        require_admin=True,
        summary="Removes a user from a group",
    )
    def delete(
        self,
        trans: ProvidesAppContext = DependsOnTrans,
        group_id: EncodedDatabaseIdField = GroupIDParam,
        user_id: EncodedDatabaseIdField = UserIDParam,
    ) -> GroupUserModel:
        """
        DELETE /api/groups/{encoded_group_id}/users/{encoded_user_id}
        Removes a user from a group
        """
        user = self.manager.delete(trans, user_id, group_id)
        return group_user_to_model(trans, group_id, user)
