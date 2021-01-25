"""
API Controller providing Galaxy Tags
"""
import logging

from fastapi import Body
# TODO: replace with Router after merging #11219
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter as APIRouter

from galaxy.managers.tags import (
    ItemTagsPayload,
    TagsManager,
)
from galaxy.structured_app import StructuredApp
from galaxy.web import expose_api
from galaxy.webapps.base.controller import BaseAPIController
from galaxy.webapps.base.webapp import GalaxyWebTransaction
from . import Depends, get_app, get_trans

log = logging.getLogger(__name__)

router = APIRouter(tags=['tags'])


def get_tags_manager(app: StructuredApp = Depends(get_app)) -> TagsManager:
    return TagsManager(app)  # TODO: remove/refactor after merging #11180


@cbv(router)
class FastAPITags:
    manager: TagsManager = Depends(get_tags_manager)

    @router.put(
        '/api/tags',
        summary="Apply a new set of tags to an item; previous tags are deleted.",
    )
    def update(
        self,
        payload: ItemTagsPayload = Body(
            ...,  # Required
            title="Payload",
            description="Request body containing the item and the tags to be assigned.",
        ),
        trans: GalaxyWebTransaction = Depends(get_trans),
    ):
        """Replaces the tags associated with an item with the new ones specified in the payload."""
        self.manager.update(trans, payload)


class TagsController(BaseAPIController):

    def __init__(self, app):
        super().__init__(app)
        self.manager = TagsManager(app)

    # Retag an item. All previous tags are deleted and new tags are applied.
    @expose_api
    def update(self, trans: GalaxyWebTransaction, payload: dict, **kwd):
        """
        PUT /api/tags/

        Apply a new set of tags to an item; previous tags are deleted.
        """
        self.manager.update(trans, ItemTagsPayload(**payload))
