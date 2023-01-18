from typing import (
    List,
    Optional,
)

from fastapi import (
    Body,
    Response,
    status,
)
from pydantic import BaseModel

import tool_shed.util.shed_util_common as suc
from galaxy.exceptions import (
    InsufficientPermissionsException,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.managers.api_keys import ApiKeyManager
from tool_shed.context import SessionRequestContext
from tool_shed.managers.users import (
    api_create_user,
    get_api_user,
    index,
)
from tool_shed_client.schema import (
    CreateUserRequest,
    User,
)
from . import (
    depends,
    DependsOnTrans,
    Router,
    UserIdPathParam,
)

router = Router(tags=["users"])


@router.cbv
class FastAPIUsers:
    api_key_manager: ApiKeyManager = depends(ApiKeyManager)

    @router.get(
        "/api/users",
        description="index users",
        operation_id="users__index",
    )
    def index(self, trans: SessionRequestContext = DependsOnTrans) -> List[User]:
        deleted = False
        return index(trans.app, deleted)

    @router.post(
        "/api/users",
        description="create a user",
        operation_id="users__create",
        require_admin=True,
    )
    def create(self, trans: SessionRequestContext = DependsOnTrans, request: CreateUserRequest = Body(...)) -> User:
        return api_create_user(trans, request)

    @router.get(
        "/api/users/current",
        description="show current user",
        operation_id="users__current",
    )
    def current(self, trans: SessionRequestContext = DependsOnTrans) -> User:
        user = trans.user
        assert user
        return get_api_user(trans.app, user)

    @router.get(
        "/api/users/{encoded_user_id}",
        description="show a user",
        operation_id="users__show",
    )
    def show(self, trans: SessionRequestContext = DependsOnTrans, encoded_user_id: str = UserIdPathParam) -> User:
        user = suc.get_user(trans.app, encoded_user_id)
        if user is None:
            raise ObjectNotFound()
        return get_api_user(trans.app, user)

    @router.get(
        "/api/users/{encoded_user_id}/api_key",
        name="get_or_create_api_key",
        summary="Return the user's API key",
        operation_id="users__get_or_create_api_key",
    )
    def get_or_create_api_key(
        self, trans: SessionRequestContext = DependsOnTrans, encoded_user_id: str = UserIdPathParam
    ) -> str:
        user = self._get_user(trans, encoded_user_id)
        return self.api_key_manager.get_or_create_api_key(user)

    @router.post(
        "/api/users/{encoded_user_id}/api_key",
        summary="Creates a new API key for the user",
        operation_id="users__create_api_key",
    )
    def create_api_key(
        self, trans: SessionRequestContext = DependsOnTrans, encoded_user_id: str = UserIdPathParam
    ) -> str:
        user = self._get_user(trans, encoded_user_id)
        return self.api_key_manager.create_api_key(user).key

    @router.delete(
        "/api/users/{encoded_user_id}/api_key",
        summary="Delete the current API key of the user",
        status_code=status.HTTP_204_NO_CONTENT,
        operation_id="users__delete_api_key",
    )
    def delete_api_key(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        encoded_user_id: str = UserIdPathParam,
    ):
        user = self._get_user(trans, encoded_user_id)
        self.api_key_manager.delete_api_key(user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    def _get_user(self, trans: SessionRequestContext, encoded_user_id: str):
        if encoded_user_id == "current":
            user = trans.user
        else:
            user = suc.get_user(trans.app, encoded_user_id)
        if user is None:
            raise ObjectNotFound()
        if not (trans.user_is_admin or trans.user == user):
            raise InsufficientPermissionsException()
        return user
