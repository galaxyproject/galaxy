"""
API operations related to tagging items.
"""
import logging

from fastapi import (
    Body,
    Path,
)

from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.item_tags import ItemTagsManager
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.item_tags import (
    ItemTagsCreatePayload,
    ItemTagsListResponse,
    ItemTagsResponse,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["item_tags"])


@router.cbv
class FastAPIItemTags:
    manager: ItemTagsManager = depends(ItemTagsManager)

    @classmethod
    def create_class(cls, prefix, tagged_item_class):
        class Temp(cls):
            @router.get(f"/api/{prefix}/{{tagged_item_id}}/tags")
            def index(
                self,
                trans: ProvidesAppContext = DependsOnTrans,
                tagged_item_id: DecodedDatabaseIdField = Path(..., title="Item ID"),
            ) -> ItemTagsListResponse:
                return self.manager.index(trans, tagged_item_class, tagged_item_id)

            @router.get(f"/api/{prefix}/{{tagged_item_id}}/tags/{{tag_name}}")
            def show(
                self,
                trans: ProvidesAppContext = DependsOnTrans,
                tagged_item_id: DecodedDatabaseIdField = Path(..., title="Item ID"),
                tag_name: str = Path(..., title="Tag Name"),
            ) -> ItemTagsResponse:
                return self.manager.show(trans, tagged_item_class, tagged_item_id, tag_name)

            @router.post(f"/api/{prefix}/{{tagged_item_id}}/tags/{{tag_name}}")
            def create(
                self,
                trans: ProvidesAppContext = DependsOnTrans,
                tagged_item_id: DecodedDatabaseIdField = Path(..., title="Item ID"),
                tag_name: str = Path(..., title="Tag Name"),
                payload: ItemTagsCreatePayload = Body(...),
            ) -> ItemTagsResponse:
                return self.manager.create(trans, tagged_item_class, tagged_item_id, tag_name, payload)

            @router.put(f"/api/{prefix}/{{tagged_item_id}}/tags/{{tag_name}}")
            def update(
                self,
                trans: ProvidesAppContext = DependsOnTrans,
                tagged_item_id: DecodedDatabaseIdField = Path(..., title="Item ID"),
                tag_name: str = Path(..., title="Tag Name"),
                payload: ItemTagsCreatePayload = Body(...),
            ) -> ItemTagsResponse:
                return self.manager.create(trans, tagged_item_class, tagged_item_id, tag_name, payload)

            @router.delete(f"/api/{prefix}/{{tagged_item_id}}/tags/{{tag_name}}")
            def delete(
                self,
                trans: ProvidesAppContext = DependsOnTrans,
                tagged_item_id: DecodedDatabaseIdField = Path(..., title="Item ID"),
                tag_name: str = Path(..., title="Tag Name"),
            ) -> bool:
                return self.manager.delete(trans, tagged_item_class, tagged_item_id, tag_name)

        return Temp


prefixs = {
    "histories": "History",
    "histories/{history_id}/contents": "HistoryDatasetAssociation",
    "workflows": "StoredWorkflow",
}
for prefix, tagged_item_class in prefixs.items():
    router.cbv(FastAPIItemTags.create_class(prefix, tagged_item_class))


# TODO: Visualization and Pages once APIs for those are available
