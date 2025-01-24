import abc
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from typing_extensions import Literal

from galaxy.managers.context import ProvidesHistoryContext
from galaxy.model import (
    GalaxySession,
    History,
    Role,
)
from galaxy.model.base import transaction


class WorkRequestContext(ProvidesHistoryContext):
    """Stripped down implementation of Galaxy web transaction god object for
    work request handling outside of web threads - uses mix-ins shared with
    GalaxyWebTransaction to provide app, user, and history context convenience
    methods - but nothing related to HTTP handling, mako views, etc....

    Things that only need app shouldn't be consuming trans - but there is a
    need for actions potentially tied to users and histories and  hopefully
    this can define that stripped down interface providing access to user and
    history information - but not dealing with web request and response
    objects.
    """

    def __init__(
        self,
        app,
        user=None,
        history=None,
        workflow_building_mode=False,
        url_builder=None,
        galaxy_session: Optional[GalaxySession] = None,
    ):
        self._app = app
        self.__user = user
        self.__user_current_roles: Optional[List[Role]] = None
        self.__history = history
        self._url_builder = url_builder
        self._short_term_cache: Dict[Tuple[str, ...], Any] = {}
        self.workflow_building_mode = workflow_building_mode
        self.galaxy_session = galaxy_session

    @property
    def app(self):
        return self._app

    @property
    def url_builder(self):
        return self._url_builder

    def get_history(self, create=False):
        return self.__history

    @property
    def history(self):
        return self.get_history()

    def get_user(self):
        """Return the current user if logged in or None."""
        return self.__user

    def get_current_user_roles(self):
        if self.__user_current_roles is None:
            self.__user_current_roles = super().get_current_user_roles()
        return self.__user_current_roles

    def set_user(self, user):
        """Set the current user."""
        raise NotImplementedError("Cannot change users from a work request context.")

    user = property(get_user, set_user)


class GalaxyAbstractRequest:
    """Abstract interface to provide access to some request properties."""

    @property
    @abc.abstractmethod
    def base(self) -> str:
        """Base URL of the request."""

    @property
    @abc.abstractmethod
    def url_path(self) -> str:
        """Base with optional prefix added."""

    @property
    @abc.abstractmethod
    def host(self) -> str:
        """The host address."""

    @property
    @abc.abstractmethod
    def is_secure(self) -> bool:
        """Was this a secure (https) request."""

    @abc.abstractmethod
    def get_cookie(self, name):
        """Return cookie."""


class GalaxyAbstractResponse:
    """Abstract interface to provide access to some response utilities."""

    @property
    @abc.abstractmethod
    def headers(self) -> dict:
        """The response headers."""

    def set_content_type(self, content_type: str):
        """
        Sets the Content-Type header
        """
        self.headers["content-type"] = content_type

    def get_content_type(self):
        return self.headers.get("content-type", None)

    @abc.abstractmethod
    def set_cookie(
        self,
        key: str,
        value: str = "",
        max_age: Optional[int] = None,
        expires: Optional[int] = None,
        path: str = "/",
        domain: Optional[str] = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Optional[Literal["lax", "strict", "none"]] = "lax",
    ) -> None:
        """Set a cookie."""


class SessionRequestContext(WorkRequestContext):
    """Like WorkRequestContext, but provides access to request."""

    def __init__(self, **kwargs):
        self.__request: GalaxyAbstractRequest = kwargs.pop("request")
        self.__response: GalaxyAbstractResponse = kwargs.pop("response")
        super().__init__(**kwargs)

    @property
    def host(self):
        return self.__request.host

    @property
    def request(self) -> GalaxyAbstractRequest:
        return self.__request

    @property
    def response(self) -> GalaxyAbstractResponse:
        return self.__response

    def get_galaxy_session(self):
        return self.galaxy_session

    def set_history(self, history):
        if history and not history.deleted and self.galaxy_session:
            self.galaxy_session.current_history = history
        self.sa_session.add(self.galaxy_session)
        with transaction(self.sa_session):
            self.sa_session.commit()


def proxy_work_context_for_history(
    trans: ProvidesHistoryContext, history: Optional[History] = None, workflow_building_mode=False
) -> WorkRequestContext:
    """Create a WorkContext for supplied context with potentially different history.

    This provides semi-structured access to a transaction/work context with a supplied target
    history that is different from the user's current history (which also might change during
    the request).
    """
    return WorkRequestContext(
        app=trans.app,
        user=trans.user,
        history=history or trans.history,
        url_builder=trans.url_builder,
        workflow_building_mode=workflow_building_mode,
        galaxy_session=trans.galaxy_session,
    )
