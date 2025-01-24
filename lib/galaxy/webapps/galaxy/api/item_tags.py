"""
API operations related to tagging items.
"""

import logging

from fastapi import (
    Body,
    Path,
)
from typing_extensions import Annotated

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
    def create_class(cls, prefix, tagged_item_class, tagged_item_id, api_docs_tag, extra_path_params):
        class Temp(cls):
            @router.get(
                f"/api/{prefix}/{{{tagged_item_id}}}/tags",
                tags=[api_docs_tag],
                summary=f"Show tags based on {tagged_item_id}",
                openapi_extra=extra_path_params,
            )
            def index(
                self,
                item_id: Annotated[DecodedDatabaseIdField, Path(..., title="Item ID", alias=tagged_item_id)],
                trans: ProvidesAppContext = DependsOnTrans,
            ) -> ItemTagsListResponse:
                return self.manager.index(trans, tagged_item_class, item_id)

            @router.get(
                f"/api/{prefix}/{{{tagged_item_id}}}/tags/{{tag_name}}",
                tags=[api_docs_tag],
                summary=f"Show tag based on {tagged_item_id}",
                openapi_extra=extra_path_params,
            )
            def show(
                self,
                item_id: Annotated[DecodedDatabaseIdField, Path(..., title="Item ID", alias=tagged_item_id)],
                trans: ProvidesAppContext = DependsOnTrans,
                tag_name: str = Path(..., title="Tag Name"),
            ) -> ItemTagsResponse:
                return self.manager.show(trans, tagged_item_class, item_id, tag_name)

            @router.post(
                f"/api/{prefix}/{{{tagged_item_id}}}/tags/{{tag_name}}",
                tags=[api_docs_tag],
                summary=f"Create tag based on {tagged_item_id}",
                openapi_extra=extra_path_params,
            )
            def create(
                self,
                item_id: Annotated[DecodedDatabaseIdField, Path(..., title="Item ID", alias=tagged_item_id)],
                trans: ProvidesAppContext = DependsOnTrans,
                tag_name: str = Path(..., title="Tag Name"),
                payload: ItemTagsCreatePayload = Body(None),
            ) -> ItemTagsResponse:
                if payload is None:
                    payload = ItemTagsCreatePayload()
                return self.manager.create(trans, tagged_item_class, item_id, tag_name, payload)

            @router.put(
                f"/api/{prefix}/{{{tagged_item_id}}}/tags/{{tag_name}}",
                tags=[api_docs_tag],
                summary=f"Update tag based on {tagged_item_id}",
                openapi_extra=extra_path_params,
            )
            def update(
                self,
                item_id: Annotated[DecodedDatabaseIdField, Path(..., title="Item ID", alias=tagged_item_id)],
                trans: ProvidesAppContext = DependsOnTrans,
                tag_name: str = Path(..., title="Tag Name"),
                payload: ItemTagsCreatePayload = Body(...),
            ) -> ItemTagsResponse:
                return self.manager.create(trans, tagged_item_class, item_id, tag_name, payload)

            @router.delete(
                f"/api/{prefix}/{{{tagged_item_id}}}/tags/{{tag_name}}",
                tags=[api_docs_tag],
                summary=f"Delete tag based on {tagged_item_id}",
                openapi_extra=extra_path_params,
            )
            def delete(
                self,
                item_id: Annotated[DecodedDatabaseIdField, Path(..., title="Item ID", alias=tagged_item_id)],
                trans: ProvidesAppContext = DependsOnTrans,
                tag_name: str = Path(..., title="Tag Name"),
            ) -> bool:
                return self.manager.delete(trans, tagged_item_class, item_id, tag_name)

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

    router.cbv(FastAPIItemTags.create_class(prefix, tagged_item_class, tagged_item_id, api_docs_tag, extra_path_params))


# TODO: Visualization and Pages once APIs for those are available
