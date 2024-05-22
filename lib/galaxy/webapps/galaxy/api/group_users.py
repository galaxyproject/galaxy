"""
API operations on Group objects.
"""

import logging

from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.group_users import GroupUsersManager
from galaxy.schema.fields import Security
from galaxy.schema.schema import (
    GroupUserListResponse,
    GroupUserResponse,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.api.common import (
    GroupIDPathParam,
    UserIdPathParam,
)

log = logging.getLogger(__name__)

router = Router(tags=["group_users"])


def group_user_to_model(trans, group_id, user) -> GroupUserResponse:
    encoded_group_id = Security.security.encode_id(group_id)
    encoded_user_id = Security.security.encode_id(user.id)
    url = trans.url_builder("group_user", group_id=encoded_group_id, user_id=encoded_user_id)
    return GroupUserResponse(id=user.id, email=user.email, url=url)


@router.cbv
class FastAPIGroupUsers:
    manager: GroupUsersManager = depends(GroupUsersManager)

    @router.get(
        "/api/groups/{group_id}/users",
        require_admin=True,
        summary="Displays a collection (list) of groups.",
        name="group_users",
    )
    def index(
        self,
        group_id: GroupIDPathParam,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> GroupUserListResponse:
        """
        GET /api/groups/{encoded_group_id}/users
        Displays a collection (list) of groups.
        """
        group_users = self.manager.index(trans, group_id)
        return GroupUserListResponse(root=[group_user_to_model(trans, group_id, gr) for gr in group_users])

    @router.get(
        "/api/groups/{group_id}/user/{user_id}",
        alias="/api/groups/{group_id}/users/{user_id}",
        name="group_user",
        require_admin=True,
        summary="Displays information about a group user.",
    )
    def show(
        self,
        group_id: GroupIDPathParam,
        user_id: UserIdPathParam,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> GroupUserResponse:
        """
        Displays information about a group user.
        """
        user = self.manager.show(trans, user_id, group_id)
        return group_user_to_model(trans, group_id, user)

    @router.put(
        "/api/groups/{group_id}/users/{user_id}",
        alias="/api/groups/{group_id}/user/{user_id}",
        require_admin=True,
        summary="Adds a user to a group",
    )
    def update(
        self,
        group_id: GroupIDPathParam,
        user_id: UserIdPathParam,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> GroupUserResponse:
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
        group_id: GroupIDPathParam,
        user_id: UserIdPathParam,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> GroupUserResponse:
        """
        DELETE /api/groups/{encoded_group_id}/users/{encoded_user_id}
        Removes a user from a group
        """
        user = self.manager.delete(trans, user_id, group_id)
        return group_user_to_model(trans, group_id, user)
