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

router = Router()


@router.cbv
class FastAPIItemTags:
    manager: ItemTagsManager = depends(ItemTagsManager)

    @classmethod
    def create_class(cls, prefix, tagged_item_class, tagged_item_id, tagged_item_tag):
        class Temp(cls):
            @router.get(
                f"/api/{prefix}/{{id}}/tags", tags=[tagged_item_tag], summary=f"Show tags based on {tagged_item_id}"
            )
            def index(
                self,
                trans: ProvidesAppContext = DependsOnTrans,
                id: DecodedDatabaseIdField = Path(..., title="Item ID", description=f"{tagged_item_id}"),
            ) -> ItemTagsListResponse:
                return self.manager.index(trans, tagged_item_class, id)

            @router.get(
                f"/api/{prefix}/{{id}}/tags/{{tag_name}}",
                tags=[tagged_item_tag],
                summary=f"Show tag based on {tagged_item_id}",
            )
            def show(
                self,
                trans: ProvidesAppContext = DependsOnTrans,
                id: DecodedDatabaseIdField = Path(..., title="Item ID", description=f"{tagged_item_id}"),
                tag_name: str = Path(..., title="Tag Name"),
            ) -> ItemTagsResponse:
                return self.manager.show(trans, tagged_item_class, id, tag_name)

            @router.post(
                f"/api/{prefix}/{{id}}/tags/{{tag_name}}",
                tags=[tagged_item_tag],
                summary=f"Create tag based on {tagged_item_id}",
            )
            def create(
                self,
                trans: ProvidesAppContext = DependsOnTrans,
                id: DecodedDatabaseIdField = Path(..., title="Item ID", description=f"{tagged_item_id}"),
                tag_name: str = Path(..., title="Tag Name"),
                payload: ItemTagsCreatePayload = Body(...),
            ) -> ItemTagsResponse:
                return self.manager.create(trans, tagged_item_class, id, tag_name, payload)

            @router.put(
                f"/api/{prefix}/{{id}}/tags/{{tag_name}}",
                tags=[tagged_item_tag],
                summary=f"Update tag based on {tagged_item_id}",
            )
            def update(
                self,
                trans: ProvidesAppContext = DependsOnTrans,
                id: DecodedDatabaseIdField = Path(..., title="Item ID", description=f"{tagged_item_id}"),
                tag_name: str = Path(..., title="Tag Name"),
                payload: ItemTagsCreatePayload = Body(...),
            ) -> ItemTagsResponse:
                return self.manager.create(trans, tagged_item_class, id, tag_name, payload)

            @router.delete(
                f"/api/{prefix}/{{id}}/tags/{{tag_name}}",
                tags=[tagged_item_tag],
                summary=f"Delete tag based on {tagged_item_id}",
            )
            def delete(
                self,
                trans: ProvidesAppContext = DependsOnTrans,
                id: DecodedDatabaseIdField = Path(..., title="Item ID", description=f"{tagged_item_id}"),
                tag_name: str = Path(..., title="Tag Name"),
            ) -> bool:
                return self.manager.delete(trans, tagged_item_class, id, tag_name)

        return Temp


prefixs = {
    "histories": ["History", "history_id", "histories"],
    "histories/{history_id}/contents": ["HistoryDatasetAssociation", "history_content_id", "histories"],
    "workflows": ["StoredWorkflow", "workflow_id", "workflows"],
}
for prefix, tagged_item in prefixs.items():
    tagged_item_class, tagged_item_id, tagged_item_tag = tagged_item
    router.cbv(FastAPIItemTags.create_class(prefix, tagged_item_class, tagged_item_id, tagged_item_tag))


# TODO: Visualization and Pages once APIs for those are available
