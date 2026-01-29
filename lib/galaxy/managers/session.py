import logging

from sqlalchemy import (
    select,
    true,
)
from sqlalchemy.orm import joinedload

from galaxy.model.base import SharedModelMapping

log = logging.getLogger(__name__)


class GalaxySessionManager:
    """Manages GalaxySession."""

    def __init__(self, model: SharedModelMapping):
        self.model = model
        self.sa_session = model.context

    def get_session_from_session_key(self, session_key: str):
        """Returns GalaxySession if session_key is valid."""
        # going through self.model since this can be used by Galaxy or Toolshed despite
        # type annotations
        stmt = (
            select(self.model.GalaxySession)
            .where(self.model.GalaxySession.session_key == session_key)
            .where(self.model.GalaxySession.is_valid == true())
            .options(joinedload(self.model.GalaxySession.user))
            .limit(1)
        )
        return self.sa_session.scalars(stmt).first()
