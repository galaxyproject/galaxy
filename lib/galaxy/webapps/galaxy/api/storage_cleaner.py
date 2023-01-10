"""
API operations on User storage management.
"""
import logging
from typing import (
    List,
    Optional,
)

from fastapi import Body

from galaxy.managers.context import ProvidesHistoryContext
from galaxy.schema.storage_cleaner import (
    CleanupStorageItemsRequest,
    DiscardedItemsSummary,
    StorageItemsCleanupResult,
    StoredItem,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.api.common import (
    LimitQueryParam,
    OffsetQueryParam,
)
from galaxy.webapps.galaxy.services.storage_cleaner import StorageCleanerService

log = logging.getLogger(__name__)


router = Router(tags=["storage management"])


@router.cbv
class FastAPIStorageCleaner:
    service: StorageCleanerService = depends(StorageCleanerService)

    @router.get(
        "/api/storage/summary/discarded/histories",
        summary="Returns information with the total storage space taken by discarded histories associated with the given user.",
    )
    def discarded_histories_summary(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> DiscardedItemsSummary:
        return self.service.get_discarded_histories_summary(trans)

    @router.get(
        "/api/storage/discarded/histories",
        summary="Returns all discarded histories associated with the given user.",
    )
    def discarded_histories(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        offset: Optional[int] = OffsetQueryParam,
        limit: Optional[int] = LimitQueryParam,
    ) -> List[StoredItem]:
        return self.service.get_discarded_histories(trans, offset, limit)

    @router.delete(
        "/api/storage/discarded/histories",
        summary="Purges histories that has been previously deleted by the user.",
    )
    def cleanup_histories(
        self, trans: ProvidesHistoryContext = DependsOnTrans, payload: CleanupStorageItemsRequest = Body(...)
    ) -> StorageItemsCleanupResult:
        return self.service.cleanup_histories(trans, set(payload.item_ids))
