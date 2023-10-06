import logging
from typing import List

import requests

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ServerNotConfiguredForRequest
from galaxy.schema.help import HelpSearchResponse
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.galaxy.services.base import ServiceBase

log = logging.getLogger(__name__)


class HelpService(ServiceBase):
    """Common interface/service logic for interactions with Galaxy Help API.

    Provides the logic of the actions invoked by API controllers and uses type definitions
    and pydantic models to declare its parameters and return types.
    """

    def __init__(
        self,
        security: IdEncodingHelper,
        config: GalaxyAppConfiguration,
    ):
        super().__init__(security)
        self.config = config

    def search_forum(self, query: str) -> HelpSearchResponse:
        """Search the Galaxy Help forum using the Discourse API."""
        if not self.config.help_forum_api_url:
            raise ServerNotConfiguredForRequest("Help forum API URL is not configured.")
        forum_search_url = f"{self.config.help_forum_api_url}/search.json"
        response = requests.get(
            url=forum_search_url,
            params={
                "q": query,
            },
        )
        return HelpSearchResponse(**response.json())
