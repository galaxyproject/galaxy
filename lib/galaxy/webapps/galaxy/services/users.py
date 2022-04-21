from galaxy import exceptions as glx_exceptions
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

    def __init__(
        self,
        security: IdEncodingHelper,
        user_manager: UserManager,
    ):
        super().__init__(security)
        self.user_manager = user_manager

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
                kwargs={"user_id": self.encode_id(trans.user.id)},
            )
