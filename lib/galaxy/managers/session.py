from sqlalchemy import (
    and_,
    true,
)
from sqlalchemy.orm import (
    joinedload,
    Session,
)

from galaxy import model


class GalaxySessionManager:
    """Manages GalaxySession."""

    def __init__(self, sa_session: Session):
        self.session = sa_session

    def get_session_from_session_key(self, session_key: str):
        """Returns GalaxySession if session_key is valid."""
        galaxy_session = self.session.query(model.GalaxySession).filter(
            and_(
                model.GalaxySession.table.c.session_key == session_key,
                model.GalaxySession.table.c.is_valid == true())
        ).options(joinedload("user")).first()
        return galaxy_session
