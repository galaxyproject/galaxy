import logging

from sqlalchemy import (
    select,
    true,
)
from sqlalchemy.orm import joinedload

from galaxy.model import (
    GalaxySession,
    History,
)
from galaxy.model.base import SharedModelMapping
from galaxy.model.security import GalaxyRBACAgent

log = logging.getLogger(__name__)


def new_history(galaxy_session: GalaxySession, security_agent: GalaxyRBACAgent):
    """
    Create a new history and associate it with the current session and
    its associated user (if set).
    """
    # Create new history
    history = History()
    # Associate with session
    history.add_galaxy_session(galaxy_session)
    # Make it the session's current history
    galaxy_session.current_history = history
    # Associate with user
    if galaxy_session.user:
        history.user = galaxy_session.user
    # Set the user's default history permissions
    security_agent.history_set_default_permissions(history)
    return history


class GalaxySessionManager:
    """Manages GalaxySession."""

    def __init__(self, model: SharedModelMapping):
        self.model = model
        self.sa_session = model.context

    def get_or_create_default_history(self, galaxy_session: GalaxySession, security_agent: GalaxyRBACAgent):
        default_history = galaxy_session.current_history
        if default_history and not default_history.deleted:
            return default_history
        # history might be deleted, reset to None
        default_history = None
        user = galaxy_session.user
        if user:
            # Look for default history that (a) has default name + is not deleted and
            # (b) has no datasets. If suitable history found, use it; otherwise, create
            # new history.
            stmt = select(History).filter_by(user=user, name=History.default_name, deleted=False)
            unnamed_histories = self.sa_session.scalars(stmt)
            for history in unnamed_histories:
                if history.empty:
                    # Found suitable default history.
                    default_history = history
                    break

            # Set or create history.
            if default_history:
                galaxy_session.current_history = default_history
        if not default_history:
            default_history = new_history(galaxy_session, security_agent)
            self.sa_session.add_all((default_history, galaxy_session))
        self.sa_session.commit()
        return default_history

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
