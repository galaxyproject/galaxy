import abc
from typing import Optional

from sqlalchemy.orm import scoped_session

from galaxy.security.idencoding import IdEncodingHelper
from galaxy.work.context import (
    GalaxyAbstractRequest,
    GalaxyAbstractResponse,
)
from tool_shed.structured_app import ToolShedApp
from tool_shed.webapp.model import (
    GalaxySession,
    User,
)
from tool_shed.webapp.model.mapping import ToolShedModelMapping


class ProvidesAppContext:
    """For transaction-like objects to provide the shed convenience layer for
    database and event handling.

    Mixed in class must provide `app` property.
    """

    @abc.abstractproperty
    def app(self) -> ToolShedApp:
        """Provide access to the shed ``app`` object."""

    @property
    def security(self) -> IdEncodingHelper:
        return self.app.security

    @property
    def sa_session(self) -> scoped_session:
        """Provide access to Galaxy's SQLAlchemy session.

        :rtype: galaxy.model.scoped_session.galaxy_scoped_session
        """
        return self.model.session

    @property
    def model(self) -> ToolShedModelMapping:
        """Provide access to Tool Shed's model mapping class."""
        return self.app.model


class ProvidesUserContext(ProvidesAppContext):
    """For transaction-like objects to provide Galaxy convenience layer for
    reasoning about users.

    Mixed in class must provide `user` and `app`
    properties.
    """

    @abc.abstractproperty
    def user(self) -> Optional[User]:
        """Provide access to the user object."""

    @property
    def anonymous(self) -> bool:
        return self.user is None

    @property
    def user_is_admin(self) -> bool:
        return self.app.config.is_admin_user(self.user)

    @property
    def user_is_bootstrap_admin(self) -> bool:
        """Master key provided so there is no real user"""
        user = self.user
        return not self.anonymous and user is not None and user.bootstrap_admin_user


class SessionRequestContext(ProvidesUserContext):
    @abc.abstractmethod
    def get_galaxy_session(self) -> Optional[GalaxySession]:
        ...

    @abc.abstractproperty
    def request(self) -> GalaxyAbstractRequest:
        ...

    @abc.abstractproperty
    def response(self) -> GalaxyAbstractResponse:
        ...
