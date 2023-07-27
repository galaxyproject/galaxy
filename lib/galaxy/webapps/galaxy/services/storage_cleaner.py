import logging
from typing import (
    Dict,
    Optional,
    Set,
)

from galaxy.managers.base import StorageCleanerManager
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.hdas import HDAStorageCleanerManager
from galaxy.managers.histories import HistoryStorageCleanerManager
from galaxy.managers.users import UserManager
from galaxy.schema.storage_cleaner import (
    StoredItemOrderBy,
    StoredItemType,
)
from galaxy.webapps.galaxy.services.base import ServiceBase

log = logging.getLogger(__name__)


class StorageCleanerService(ServiceBase):
    """Service providing actions to monitor and recover storage space used by the user."""

    def __init__(
        self,
        user_manager: UserManager,
        history_cleaner: HistoryStorageCleanerManager,
        hda_cleaner: HDAStorageCleanerManager,
    ):
        self.user_manager = user_manager
        self.history_cleaner = history_cleaner
        self.hda_cleaner = hda_cleaner
        self.storage_cleaner_map: Dict[StoredItemType, StorageCleanerManager] = {
            "history": self.history_cleaner,
            "dataset": self.hda_cleaner,
        }

    def get_discarded_summary(self, trans: ProvidesHistoryContext, stored_item_type: StoredItemType):
        user = self.get_authenticated_user(trans)
        return self.storage_cleaner_map[stored_item_type].get_discarded_summary(user)

    def get_discarded(
        self,
        trans: ProvidesHistoryContext,
        stored_item_type: StoredItemType,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        order: Optional[StoredItemOrderBy] = None,
    ):
        user = self.get_authenticated_user(trans)
        return self.storage_cleaner_map[stored_item_type].get_discarded(user, offset, limit, order)

    def get_archived_summary(self, trans: ProvidesHistoryContext, stored_item_type: StoredItemType):
        user = self.get_authenticated_user(trans)
        return self.storage_cleaner_map[stored_item_type].get_archived_summary(user)

    def get_archived(
        self,
        trans: ProvidesHistoryContext,
        stored_item_type: StoredItemType,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        order: Optional[StoredItemOrderBy] = None,
    ):
        user = self.get_authenticated_user(trans)
        return self.storage_cleaner_map[stored_item_type].get_archived(user, offset, limit, order)

    def cleanup_items(self, trans: ProvidesHistoryContext, stored_item_type: StoredItemType, item_ids: Set[int]):
        user = self.get_authenticated_user(trans)
        return self.storage_cleaner_map[stored_item_type].cleanup_items(user, item_ids)
