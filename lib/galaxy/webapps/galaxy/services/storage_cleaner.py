import logging
from typing import (
    Optional,
    Set,
)

from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.histories import HistoryManager
from galaxy.managers.users import UserManager
from galaxy.webapps.galaxy.services.base import ServiceBase

log = logging.getLogger(__name__)


class StorageCleanerService(ServiceBase):
    """Service providing actions to monitor and recover storage space used by the user."""

    def __init__(
        self,
        user_manager: UserManager,
        history_manager: HistoryManager,
    ):
        self.user_manager = user_manager
        self.history_manager = history_manager

    def get_discarded_histories_summary(self, trans: ProvidesHistoryContext):
        user = self.get_authenticated_user(trans)
        return self.history_manager.get_discarded_summary(user)

    def get_discarded_histories(
        self, trans: ProvidesHistoryContext, offset: Optional[int] = None, limit: Optional[int] = None
    ):
        user = self.get_authenticated_user(trans)
        return self.history_manager.get_discarded(user, offset, limit)

    def cleanup_histories(self, trans: ProvidesHistoryContext, item_ids: Set[int]):
        user = self.get_authenticated_user(trans)
        return self.history_manager.cleanup_items(user, item_ids)
