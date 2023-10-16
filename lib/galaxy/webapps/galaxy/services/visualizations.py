import logging

from typing import (
    Any,
    List,
)

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
    FilterQueryParams,
    SerializationParams,
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
        trans: ProvidesHistoryContext,
        serialization_params: SerializationParams,
    ) -> List[Any]:
        """
        Search visualizations using a query system and returns a list
        containing visualization information.
        """
        user = self.get_authenticated_user(trans)
        visualizations = self.get_visualizations_by_user(trans, user)
        visualizations += self.get_visualizations_shared_with_user(trans, user)
        visualizations += self.get_published_visualizations(trans, exclude_user=user)
        return [
            self.serializer.serialize_to_view(
                content, user=user, trans=trans, **serialization_params.dict()
            )
            for content in visualizations
        ]

    def get_visualizations_by_user(self, trans, user):
        """Return query results of visualizations filtered by a user."""
        stmt = select(Visualization).filter(Visualization.user == user).order_by(Visualization.title)
        return trans.sa_session.scalars(stmt).all()

    def get_visualizations_shared_with_user(self, trans, user):
        """Return query results for visualizations shared with the given user."""
        # The second `where` clause removes duplicates when a user shares with themselves.
        stmt = (
            select(Visualization)
            .join(VisualizationUserShareAssociation)
            .where(VisualizationUserShareAssociation.user_id == user.id)
            .where(Visualization.user_id != user.id)
            .order_by(Visualization.title)
        )
        return trans.sa_session.scalars(stmt).all()

    def get_published_visualizations(self, trans, exclude_user=None):
        """
        Return query results for published visualizations optionally excluding the user in `exclude_user`.
        """
        stmt = select(Visualization).filter(Visualization.published == true())
        if exclude_user:
            stmt = stmt.filter(Visualization.user != exclude_user)
        stmt = stmt.order_by(Visualization.title)
        return trans.sa_session.scalars(stmt).all()