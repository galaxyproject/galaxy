from sqlalchemy import (
    and_,
    true,
)
from sqlalchemy.orm import (
    joinedload,
)


class GalaxySessionManager:
    """Manages GalaxySession."""

    def __init__(self, model):
        self.model = model

    def get_session_from_session_key(self, session_key: str):
        """Returns GalaxySession if session_key is valid."""
        galaxy_session = self.model.session.query(self.model.GalaxySession).filter(
            and_(
                self.model.GalaxySession.table.c.session_key == session_key,
                self.model.GalaxySession.table.c.is_valid == true())
        ).options(joinedload("user")).first()
        return galaxy_session
