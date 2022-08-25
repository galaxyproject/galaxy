from galaxy import exceptions as glx_exceptions
from galaxy.managers import api_keys
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.users import UserManager
from galaxy.queue_worker import send_local_control_task
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

    def get_api_keys(self, trans: ProvidesUserContext):
        result = []
        api_keys = self.api_key_manager.get_api_keys(trans.user)
        if api_keys:
            # Only return the last created key
            result.append({"key": api_keys[0].key, "create_time": api_keys[0].create_time})
        return result

    def create_api_key(self, trans: ProvidesUserContext):
        api_key = self.api_key_manager.create_api_key(trans.user)
        result = {"key": api_key.key, "create_time": api_key.create_time}
        return result

    def delete_api_key(
        self,
        api_key: str,
        trans: ProvidesUserContext,
    ):
        self.api_key_manager.delete_api_key(trans.user, api_key)
