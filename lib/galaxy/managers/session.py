import logging

from sqlalchemy import (
    and_,
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
        galaxy_session = (
            self.sa_session.query(self.model.GalaxySession)
            .filter(
                and_(
                    self.model.GalaxySession.table.c.session_key == session_key,
                    self.model.GalaxySession.table.c.is_valid == true(),
                )
            )
            .options(joinedload(self.model.GalaxySession.user))
            .first()
        )
        return galaxy_session
