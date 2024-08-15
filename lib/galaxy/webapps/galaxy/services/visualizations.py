import logging
from typing import Tuple

from galaxy import exceptions
from galaxy.managers.visualizations import (
    VisualizationManager,
    VisualizationSerializer,
)
from galaxy.schema.visualization import (
    VisualizationIndexQueryPayload,
    VisualizationSummaryList,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.galaxy.services.base import ServiceBase
from galaxy.webapps.galaxy.services.notifications import NotificationService
from galaxy.webapps.galaxy.services.sharable import ShareableService

log = logging.getLogger(__name__)


class VisualizationsService(ServiceBase):
    """Common interface/service logic for interactions with visualizations in the context of the API.

    Provides the logic of the actions invoked by API controllers and uses type definitions
    and pydantic models to declare its parameters and return types.
    """

    def __init__(
        self,
        security: IdEncodingHelper,
        manager: VisualizationManager,
        serializer: VisualizationSerializer,
        notification_service: NotificationService,
    ):
        super().__init__(security)
        self.manager = manager
        self.serializer = serializer
        self.shareable_service = ShareableService(self.manager, self.serializer, notification_service)

    # TODO: add the rest of the API actions here and call them directly from the API controller

    def index(
        self,
        trans,
        payload: VisualizationIndexQueryPayload,
        include_total_count: bool = False,
    ) -> Tuple[VisualizationSummaryList, int]:
        """Return a list of Visualizations viewable by the user

        :rtype:     list
        :returns:   dictionaries containing Visualization details
        """
        if not trans.user_is_admin:
            user_id = trans.user and trans.user.id
            if payload.user_id and payload.user_id != user_id:
                raise exceptions.AdminRequiredException("Only admins can index the visualizations of others")

        entries, total_matches = self.manager.index_query(trans, payload, include_total_count)
        return (
            VisualizationSummaryList(root=[entry.to_dict() for entry in entries]),
            total_matches,
        )
