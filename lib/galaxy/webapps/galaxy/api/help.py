import logging

from fastapi import Query
from typing_extensions import Annotated

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.help import HelpForumSearchResponse
from galaxy.webapps.galaxy.services.help import HelpService
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)


router = Router(tags=["help"])


@router.cbv
class HelpAPI:
    service: HelpService = depends(HelpService)

    @router.get(
        "/api/help/forum/search",
        summary="Search the Galaxy Help forum.",
    )
    def search_forum(
        self,
        query: Annotated[str, Query(description="Search query to use for searching the Galaxy Help forum.")],
        trans: ProvidesUserContext = DependsOnTrans,  # Require session or API key, don't make public
    ) -> HelpForumSearchResponse:
        """Search the Galaxy Help forum using the Discourse API.

        **Note**: This endpoint is for **INTERNAL USE ONLY** and is not part of the public Galaxy API.
        """
        return self.service.search_forum(query)
