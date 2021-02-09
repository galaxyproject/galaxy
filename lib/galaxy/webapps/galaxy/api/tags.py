"""
API Controller providing Galaxy Tags
"""
import logging

from fastapi import (
    Body,
    status,
)
# TODO: replace with Router after merging #11219
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter as APIRouter

from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.tags import (
    ItemTagsPayload,
    TagsManager,
)
from galaxy.web import expose_api
from galaxy.webapps.base.controller import BaseAPIController
from . import (
    Depends,
    get_trans,
)

log = logging.getLogger(__name__)

# TODO: This FastAPI router is disabled. Please rename it to `router` when the database session issues are fixed.
_router = APIRouter(tags=['tags'])


def get_tags_manager() -> TagsManager:
    return TagsManager()  # TODO: remove/refactor after merging #11180


@cbv(_router)
class FastAPITags:
    manager: TagsManager = Depends(get_tags_manager)

    @_router.put(
        '/api/tags',
        summary="Apply a new set of tags to an item.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def update(
        self,
        trans: ProvidesUserContext = Depends(get_trans),
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


class TagsController(BaseAPIController):

    def __init__(self, app):
        super().__init__(app)
        self.manager = TagsManager()

    # Retag an item. All previous tags are deleted and new tags are applied.
    @expose_api
    def update(self, trans: ProvidesUserContext, payload: dict, **kwd):
        """
        PUT /api/tags/

        Apply a new set of tags to an item; previous tags are deleted.
        """
        self.manager.update(trans, ItemTagsPayload(**payload))
