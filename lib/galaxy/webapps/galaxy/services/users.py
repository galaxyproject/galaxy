from typing import Optional

from galaxy import exceptions as glx_exceptions
from galaxy.managers import api_keys
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.users import UserManager
from galaxy.queue_worker import send_local_control_task
from galaxy.schema import APIKeyModel
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.galaxy.services.base import ServiceBase


class UsersService(ServiceBase):
    """Common interface/service logic for interactions with users in the context of the API.

    Provides the logic of the actions invoked by API controllers and uses type definitions
    and pydantic models to declare its parameters and return types.
    """

    def __init__(self, security: IdEncodingHelper, user_manager: UserManager, api_key_manager: api_keys.ApiKeyManager):
        super().__init__(security)
        self.user_manager = user_manager
        self.api_key_manager = api_key_manager

    def recalculate_disk_usage(
        self,
        trans: ProvidesUserContext,
    ):
        if trans.anonymous:
            raise glx_exceptions.AuthenticationRequired("Only registered users can recalculate disk usage.")
        if trans.app.config.enable_celery_tasks:
            from galaxy.celery.tasks import recalculate_user_disk_usage

            recalculate_user_disk_usage.delay(user_id=trans.user.id)
        else:
            send_local_control_task(
                trans.app,
                "recalculate_user_disk_usage",
                kwargs={"user_id": trans.user.id},
            )

    def get_api_key(self, trans: ProvidesUserContext, user_id: int) -> Optional[APIKeyModel]:
        """Returns the current API key or None if the user doesn't have any valid API key."""
        user = self._get_user(trans, user_id)
        api_key = self.api_key_manager.get_api_key(user)
        return APIKeyModel.construct(key=api_key.key, create_time=api_key.create_time) if api_key else None

    def get_or_create_api_key(self, trans: ProvidesUserContext, user_id: int) -> str:
        """Returns the current API key (as plain string) or creates a new one."""
        user = self._get_user(trans, user_id)
        return self.api_key_manager.get_or_create_api_key(user)

    def create_api_key(self, trans: ProvidesUserContext, user_id: int) -> APIKeyModel:
        """Creates a new API key for the given user"""
        user = self._get_user(trans, user_id)
        api_key = self.api_key_manager.create_api_key(user)
        result = APIKeyModel.construct(key=api_key.key, create_time=api_key.create_time)
        return result

    def delete_api_key(self, trans: ProvidesUserContext, user_id: int) -> None:
        """Deletes a particular API key"""
        user = self._get_user(trans, user_id)
        self.api_key_manager.delete_api_key(user)

    def _get_user(self, trans: ProvidesUserContext, user_id):
        user = trans.user
        if trans.anonymous or (user and user.id != user_id and not trans.user_is_admin):
            raise glx_exceptions.InsufficientPermissionsException("Access denied.")
        user = self.user_manager.by_id(user_id)
        return user
