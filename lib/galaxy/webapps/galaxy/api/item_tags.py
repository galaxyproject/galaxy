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


class FastAPIItemTags:
    @classmethod
    def create_class(cls, prefix, tagged_item_class, tagged_item_id, api_docs_tag, extra_path_params):
        class Temp(cls):
            @router.get(
                f"/api/{prefix}/{{{tagged_item_id}}}/tags",
                tags=[api_docs_tag],
                summary=f"Show tags based on {tagged_item_id}",
                openapi_extra=extra_path_params,
            )
            def index(
                trans: ProvidesAppContext = DependsOnTrans,
                item_id: DecodedDatabaseIdField = Path(..., title="Item ID", alias=tagged_item_id),
                manager: ItemTagsManager = depends(ItemTagsManager),
            ) -> ItemTagsListResponse:
                return manager.index(trans, tagged_item_class, item_id)

            @router.get(
                f"/api/{prefix}/{{{tagged_item_id}}}/tags/{{tag_name}}",
                tags=[api_docs_tag],
                summary=f"Show tag based on {tagged_item_id}",
                openapi_extra=extra_path_params,
            )
            def show(
                trans: ProvidesAppContext = DependsOnTrans,
                item_id: DecodedDatabaseIdField = Path(..., title="Item ID", alias=tagged_item_id),
                tag_name: str = Path(..., title="Tag Name"),
                manager: ItemTagsManager = depends(ItemTagsManager),
            ) -> ItemTagsResponse:
                return manager.show(trans, tagged_item_class, item_id, tag_name)

            @router.post(
                f"/api/{prefix}/{{{tagged_item_id}}}/tags/{{tag_name}}",
                tags=[api_docs_tag],
                summary=f"Create tag based on {tagged_item_id}",
                openapi_extra=extra_path_params,
            )
            def create(
                trans: ProvidesAppContext = DependsOnTrans,
                item_id: DecodedDatabaseIdField = Path(..., title="Item ID", alias=tagged_item_id),
                tag_name: str = Path(..., title="Tag Name"),
                payload: ItemTagsCreatePayload = Body(None),
                manager: ItemTagsManager = depends(ItemTagsManager),
            ) -> ItemTagsResponse:
                if payload is None:
                    payload = ItemTagsCreatePayload()
                return manager.create(trans, tagged_item_class, item_id, tag_name, payload)

            @router.put(
                f"/api/{prefix}/{{{tagged_item_id}}}/tags/{{tag_name}}",
                tags=[api_docs_tag],
                summary=f"Update tag based on {tagged_item_id}",
                openapi_extra=extra_path_params,
            )
            def update(
                trans: ProvidesAppContext = DependsOnTrans,
                item_id: DecodedDatabaseIdField = Path(..., title="Item ID", alias=tagged_item_id),
                tag_name: str = Path(..., title="Tag Name"),
                payload: ItemTagsCreatePayload = Body(...),
                manager: ItemTagsManager = depends(ItemTagsManager),
            ) -> ItemTagsResponse:
                return manager.create(trans, tagged_item_class, item_id, tag_name, payload)

            @router.delete(
                f"/api/{prefix}/{{{tagged_item_id}}}/tags/{{tag_name}}",
                tags=[api_docs_tag],
                summary=f"Delete tag based on {tagged_item_id}",
                openapi_extra=extra_path_params,
            )
            def delete(
                trans: ProvidesAppContext = DependsOnTrans,
                item_id: DecodedDatabaseIdField = Path(..., title="Item ID", alias=tagged_item_id),
                tag_name: str = Path(..., title="Tag Name"),
                manager: ItemTagsManager = depends(ItemTagsManager),
            ) -> bool:
                return manager.delete(trans, tagged_item_class, item_id, tag_name)

        return Temp


prefixes = {
    "histories": ["History", "history_id", "histories"],
    "histories/{history_id}/contents": ["HistoryDatasetAssociation", "history_content_id", "histories"],
    "workflows": ["StoredWorkflow", "workflow_id", "workflows"],
}
for prefix, tagged_item in prefixes.items():
    tagged_item_class, tagged_item_id, api_docs_tag = tagged_item
    extra_path_params = None
    if tagged_item_id == "history_content_id":
        extra_path_params = {
            "parameters": [
                {
                    "in": "path",
                    "name": "history_id",
                    "required": True,
                    "schema": {"title": "History ID", "type": "string"},
                }
            ]
        }

    FastAPIItemTags.create_class(prefix, tagged_item_class, tagged_item_id, api_docs_tag, extra_path_params)


# TODO: Visualization and Pages once APIs for those are available
