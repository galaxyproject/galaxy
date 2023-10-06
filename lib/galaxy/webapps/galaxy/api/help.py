import logging
from typing import List

from fastapi import Query
from typing_extensions import Annotated

from galaxy.schema.help import HelpSearchResponse
from galaxy.webapps.galaxy.services.help import HelpService
from . import (
    depends,
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
        term: Annotated[str, Query(description="Search term to use for searching the Galaxy Help forum.")],
        tags: Annotated[List[str], Query(description="List of tags to filter the search results by.")],
    ) -> HelpSearchResponse:
        return self.service.search_forum(term=term, tags=tags)
