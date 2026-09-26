"""
API Controller providing Galaxy Tags
"""

import logging

from fastapi import (
    Body,
    Response,
    status,
)

from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.tags import (
    ItemTagsPayload,
    TagsManager,
)
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["tags"])


@router.cbv
class FastAPITags:
    manager: TagsManager = depends(TagsManager)

    @router.put(
        "/api/tags",
        summary="Apply a new set of tags to an item.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def update(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: ItemTagsPayload = Body(
            ...,  # Required
            title="Payload",
            description="Request body containing the item and the tags to be assigned.",
        ),
    ):
        """Replaces the tags associated with an item with the new ones specified in the payload.

        - The previous tags will be __deleted__.
        - If no tags are provided in the request body, the currently associated tags will also be __deleted__.
        """
        self.manager.update(trans, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
