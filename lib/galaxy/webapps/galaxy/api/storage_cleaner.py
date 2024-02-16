"""
API operations on User storage management.
"""

import logging
from typing import (
    List,
    Optional,
)

from fastapi import (
    Body,
    Query,
)

from galaxy.managers.context import ProvidesHistoryContext
from galaxy.schema.storage_cleaner import (
    CleanableItemsSummary,
    CleanupStorageItemsRequest,
    StorageItemsCleanupResult,
    StoredItem,
    StoredItemOrderBy,
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

OrderQueryParam: Optional[StoredItemOrderBy] = Query(
    default=None,
    title="Order",
    description=(
        "String containing one of the valid ordering attributes followed "
        "by '-asc' or '-dsc' for ascending and descending order respectively."
    ),
)


@router.cbv
class FastAPIStorageCleaner:
    service: StorageCleanerService = depends(StorageCleanerService)

    @router.get(
        "/api/storage/histories/discarded/summary",
        summary="Returns information with the total storage space taken by discarded histories associated with the given user.",
    )
    def discarded_histories_summary(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> CleanableItemsSummary:
        return self.service.get_discarded_summary(trans, stored_item_type="history")

    @router.get(
        "/api/storage/histories/discarded",
        summary="Returns all discarded histories associated with the given user.",
    )
    def discarded_histories(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        offset: Optional[int] = OffsetQueryParam,
        limit: Optional[int] = LimitQueryParam,
        order: Optional[StoredItemOrderBy] = OrderQueryParam,
    ) -> List[StoredItem]:
        return self.service.get_discarded(trans, "history", offset, limit, order)

    @router.delete(
        "/api/storage/histories",
        summary="Purges a set of histories by ID. The histories must be owned by the user.",
    )
    def cleanup_histories(
        self, trans: ProvidesHistoryContext = DependsOnTrans, payload: CleanupStorageItemsRequest = Body(...)
    ) -> StorageItemsCleanupResult:
        """
        **Warning**: This operation cannot be undone. All objects will be deleted permanently from the disk.
        """
        return self.service.cleanup_items(trans, stored_item_type="history", item_ids=set(payload.item_ids))

    @router.get(
        "/api/storage/datasets/discarded/summary",
        summary="Returns information with the total storage space taken by discarded datasets owned by the given user.",
    )
    def discarded_datasets_summary(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> CleanableItemsSummary:
        return self.service.get_discarded_summary(trans, stored_item_type="dataset")

    @router.get(
        "/api/storage/datasets/discarded",
        summary="Returns discarded datasets owned by the given user. The results can be paginated.",
    )
    def discarded_datasets(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        offset: Optional[int] = OffsetQueryParam,
        limit: Optional[int] = LimitQueryParam,
        order: Optional[StoredItemOrderBy] = OrderQueryParam,
    ) -> List[StoredItem]:
        return self.service.get_discarded(trans, "dataset", offset, limit, order)

    @router.delete(
        "/api/storage/datasets",
        summary="Purges a set of datasets by ID from disk. The datasets must be owned by the user.",
    )
    def cleanup_datasets(
        self, trans: ProvidesHistoryContext = DependsOnTrans, payload: CleanupStorageItemsRequest = Body(...)
    ) -> StorageItemsCleanupResult:
        """
        **Warning**: This operation cannot be undone. All objects will be deleted permanently from the disk.
        """
        return self.service.cleanup_items(trans, stored_item_type="dataset", item_ids=set(payload.item_ids))

    @router.get(
        "/api/storage/histories/archived/summary",
        summary="Returns information with the total storage space taken by non-purged archived histories associated with the given user.",
    )
    def archived_histories_summary(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> CleanableItemsSummary:
        return self.service.get_archived_summary(trans, stored_item_type="history")

    @router.get(
        "/api/storage/histories/archived",
        summary="Returns archived histories owned by the given user that are not purged. The results can be paginated.",
    )
    def archived_histories(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        offset: Optional[int] = OffsetQueryParam,
        limit: Optional[int] = LimitQueryParam,
        order: Optional[StoredItemOrderBy] = OrderQueryParam,
    ) -> List[StoredItem]:
        return self.service.get_archived(trans, "history", offset, limit, order)
