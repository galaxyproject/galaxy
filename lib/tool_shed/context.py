import abc
from typing import Optional

from sqlalchemy.orm import scoped_session
from typing_extensions import Protocol

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


class ProvidesAppContext(Protocol):
    """For transaction-like objects to provide the shed convenience layer for
    database and event handling.

    Mixed in class must provide `app` property.
    """

    @property
    @abc.abstractmethod
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


class ProvidesUserContext(ProvidesAppContext, Protocol):
    """For transaction-like objects to provide Galaxy convenience layer for
    reasoning about users.

    Mixed in class must provide `user` and `app`
    properties.
    """

    @property
    @abc.abstractmethod
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


class ProvidesRepositoriesContext(ProvidesUserContext, Protocol):
    @property
    @abc.abstractmethod
    def repositories_hostname(self) -> str:
        """Provide access to hostname used by target mercurial server."""


class SessionRequestContext(ProvidesRepositoriesContext, Protocol):
    @abc.abstractmethod
    def get_galaxy_session(self) -> Optional[GalaxySession]: ...

    @abc.abstractmethod
    def set_galaxy_session(self, galaxy_session: GalaxySession): ...

    @property
    @abc.abstractmethod
    def request(self) -> GalaxyAbstractRequest: ...

    @property
    @abc.abstractmethod
    def response(self) -> GalaxyAbstractResponse: ...

    @abc.abstractmethod
    def url_builder(self): ...

    @property
    @abc.abstractmethod
    def session_csrf_token(self) -> str: ...


class SessionRequestContextImpl(SessionRequestContext):
    _app: ToolShedApp
    _user: Optional[User]
    _galaxy_session: Optional[GalaxySession]

    def __init__(
        self,
        app: ToolShedApp,
        request: GalaxyAbstractRequest,
        response: GalaxyAbstractResponse,
        user: Optional[User] = None,
        galaxy_session: Optional[GalaxySession] = None,
        url_builder=None,
    ):
        self._app = app
        self._user = user
        self._galaxy_session = galaxy_session
        self._url_builder = url_builder
        self.__request = request
        self.__response = response

    @property
    def app(self) -> ToolShedApp:
        return self._app

    @property
    def url_builder(self):
        return self._url_builder

    @property
    def user(self) -> Optional[User]:
        return self._user

    def get_galaxy_session(self) -> Optional[GalaxySession]:
        return self._galaxy_session

    def set_galaxy_session(self, galaxy_session: GalaxySession):
        self._galaxy_session = galaxy_session
        if galaxy_session.user:
            self._user = galaxy_session.user

    @property
    def repositories_hostname(self) -> str:
        return str(self.request.base).rstrip("/")

    @property
    def host(self):
        return self.__request.host

    @property
    def request(self) -> GalaxyAbstractRequest:
        return self.__request

    @property
    def response(self) -> GalaxyAbstractResponse:
        return self.__response

    # Following three things added v2.0 frontend
    @property
    def session_csrf_token(self):
        token = ""
        if self._galaxy_session:
            token = self.security.encode_id(self._galaxy_session.id, kind="csrf")
        return token

    @property
    def galaxy_session(self) -> Optional[GalaxySession]:
        return self._galaxy_session

    def log_event(self, str):
        pass
