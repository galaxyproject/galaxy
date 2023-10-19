import logging

from typing import (
    Any,
    List,
    Tuple,
)

from galaxy import exceptions

from sqlalchemy import (
    select,
    true,
)
from galaxy.model import (Visualization, VisualizationUserShareAssociation)

from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.notification import NotificationManager
from galaxy.managers.visualizations import (
    VisualizationManager,
    VisualizationSerializer,
)
from galaxy.security.idencoding import IdEncodingHelper

from galaxy.schema import (
    SerializationParams,
)
from galaxy.schema.schema import (
    VisualizationDetailsList,
    VisualizationIndexQueryPayload,
)
from galaxy.webapps.galaxy.services.base import ServiceBase
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
        notification_manager: NotificationManager,
    ):
        super().__init__(security)
        self.manager = manager
        self.serializer = serializer
        self.shareable_service = ShareableService(self.manager, self.serializer, notification_manager)

    # TODO: add the rest of the API actions here and call them directly from the API controller

    def index(
        self,
        trans,
        serialization_params: SerializationParams,
        payload: VisualizationIndexQueryPayload,
        include_total_count: bool = False
    ) -> Tuple[List[Any], int]:
        """Return a list of Visualizations viewable by the user

        :rtype:     list
        :returns:   dictionaries containing summary or detailed Visualization information
        """
        if not trans.user_is_admin:
            user_id = trans.user and trans.user.id
            if payload.user_id and payload.user_id != user_id:
                raise exceptions.AdminRequiredException("Only admins can index the visualizations of others")

        entries, total_matches = self.manager.index_query(trans, payload, include_total_count)
        response = [self.serializer.serialize_to_view(
            content, user=trans.user, trans=trans, **serialization_params.dict()
        ) for content in entries]

        return (
            response,
            total_matches,
        )
