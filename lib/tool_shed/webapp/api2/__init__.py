import logging
from json import JSONDecodeError
from typing import (
    AsyncGenerator,
    cast,
    List,
    Optional,
    Type,
    TypeVar,
)

from fastapi import (
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    Security,
)
from fastapi.security import (
    APIKeyCookie,
    APIKeyHeader,
    APIKeyQuery,
)
from pydantic import BaseModel
from starlette_context import context as request_context

from galaxy.exceptions import AdminRequiredException
from galaxy.managers.session import GalaxySessionManager
from galaxy.managers.users import UserManager
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.util import unicodify
from galaxy.web.framework.decorators import require_admin_message
from galaxy.webapps.base.webapp import create_new_session
from galaxy.webapps.galaxy.api import (
    depends as framework_depends,
    FrameworkRouter,
    GalaxyASGIRequest,
    GalaxyASGIResponse,
    T,
    UrlBuilder,
)
from tool_shed.context import (
    SessionRequestContext,
    SessionRequestContextImpl,
)
from tool_shed.structured_app import ToolShedApp
from tool_shed.webapp import app as tool_shed_app_mod
from tool_shed.webapp.model import (
    GalaxySession,
    User,
)
from tool_shed_client.schema import IndexSortByType

log = logging.getLogger(__name__)


def get_app() -> ToolShedApp:
    if tool_shed_app_mod.app is None:
        raise Exception("Failed to initialize the tool shed app correctly for FastAPI")
    return cast(ToolShedApp, tool_shed_app_mod.app)


async def get_app_with_request_session() -> AsyncGenerator[ToolShedApp, None]:
    app = get_app()
    request_id = request_context.data["X-Request-ID"]
    app.model.set_request_id(request_id)
    try:
        yield app
    finally:
        app.model.unset_request_id(request_id)


DependsOnApp = cast(ToolShedApp, Depends(get_app_with_request_session))
AUTH_COOKIE_NAME = "galaxycommunitysession"

api_key_query = APIKeyQuery(name="key", auto_error=False)
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)
api_key_cookie = APIKeyCookie(name=AUTH_COOKIE_NAME, auto_error=False)


def depends(dep_type: Type[T]) -> T:
    return framework_depends(dep_type, app=get_app_with_request_session)


def get_api_user(
    user_manager: UserManager = depends(UserManager),
    key: str = Security(api_key_query),
    x_api_key: str = Security(api_key_header),
) -> Optional[User]:
    api_key = key or x_api_key
    if not api_key:
        return None
    user = user_manager.by_api_key(api_key=api_key)
    return user


def get_session_manager(app: ToolShedApp = DependsOnApp) -> GalaxySessionManager:
    # TODO: find out how to adapt dependency for Galaxy/Report/TS
    return GalaxySessionManager(app.model)


def get_session(
    session_manager=cast(GalaxySessionManager, Depends(get_session_manager)),
    security: IdEncodingHelper = depends(IdEncodingHelper),
    galaxysession: str = Security(api_key_cookie),
) -> Optional[GalaxySession]:
    if galaxysession:
        session_key = security.decode_guid(galaxysession)
        if session_key:
            return session_manager.get_session_from_session_key(session_key)
        # TODO: What should we do if there is no session? Since this is the API, maybe nothing is the right choice?
    return None


def get_user(
    galaxy_session=cast(Optional[GalaxySession], Depends(get_session)),
    api_user=cast(Optional[User], Depends(get_api_user)),
) -> Optional[User]:
    if galaxy_session:
        return galaxy_session.user
    return api_user


def get_trans(
    request: Request,
    response: Response,
    app: ToolShedApp = DependsOnApp,
    user=cast(Optional[User], Depends(get_user)),
    galaxy_session=cast(Optional[GalaxySession], Depends(get_session)),
) -> SessionRequestContext:
    url_builder = UrlBuilder(request)
    galaxy_request = GalaxyASGIRequest(request)
    galaxy_response = GalaxyASGIResponse(response)
    return SessionRequestContextImpl(
        app,
        galaxy_request,
        galaxy_response,
        user=user,
        galaxy_session=galaxy_session,
        url_builder=url_builder,
    )


DependsOnTrans: SessionRequestContext = cast(SessionRequestContext, Depends(get_trans))


def get_admin_user(trans: SessionRequestContext = DependsOnTrans):
    if not trans.user_is_admin:
        raise AdminRequiredException(require_admin_message(trans.app.config, trans.user))
    return trans.user


AdminUserRequired = Depends(get_admin_user)


class Router(FrameworkRouter):
    admin_user_dependency = AdminUserRequired


B = TypeVar("B", bound=BaseModel)


# async def depend_on_either_json_or_form_data(model: Type[T]):
#    return Depends(get_body)


def depend_on_either_json_or_form_data(model: Type[B]) -> B:
    async def get_body(request: Request):
        content_type = request.headers.get("Content-Type")
        if content_type is None:
            raise HTTPException(status_code=400, detail="No Content-Type provided!")
        elif content_type == "application/json":
            try:
                return model(**await request.json())
            except JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON data")
        elif content_type == "application/x-www-form-urlencoded" or content_type.startswith("multipart/form-data"):
            try:
                return model(**await request.form())
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid Form data")
        else:
            raise HTTPException(status_code=400, detail="Content-Type not supported!")

    return Depends(get_body)


UserIdPathParam: str = Path(..., title="User ID", description="The encoded database identifier of the user.")

RequiredRepoOwnerParam: str = Query(
    title="owner",
    description="Owner of the target repository.",
)

RequiredRepoNameParam: str = Query(
    title="Name",
    description="Name of the target repository.",
)

RequiredChangesetParam: str = Query(
    title="changeset",
    description="Changeset of the target repository.",
)

RepositoryIdPathParam: str = Path(
    ..., title="Repository ID", description="The encoded database identifier of the repository."
)

ChangesetRevisionPathParam: str = Path(
    ...,
    title="Change Revision",
    description="The changeset revision corresponding to the target revision of the target repository.",
)

UsernameIdPathParam: str = Path(..., title="Username", description="The target username.")

CommitMessageQueryParam: Optional[str] = Query(
    default=None,
    title="Commit Message",
    description="Set commit message as a query parameter.",
)

DownloadableQueryParam: bool = Query(
    default=True,
    title="downloadable_only",
    description="Include only downloadable repositories.",
)

CommitMessage: str = Query(
    None,
    title="Commit message",
    description="A commit message to store with repository update.",
)

RepositoryIndexQueryParam: Optional[str] = Query(
    default=None,
    title="Search Query",
    description="This will perform a full search with whoosh on the backend and will cause the API endpoint to return a RepositorySearchResult. This should not be used with the 'filter' parameter.",
)

RepositoryIndexFilterParam: Optional[str] = Query(
    default=None,
    title="Filter Text",
    description="This will perform a quick search using database operators. This should not be used with the 'q' parameter.",
)

RepositoryIndexSortByParam: IndexSortByType = Query(
    default="name",
    title="Sort by",
    description="Sort by the this repository field - direction is controlled by sort_desc that defaults to False and causes an ascending sort on this field. This field is ignored if 'q' is specified an whoosh search is used.",
)

RepositoryIndexSortDescParam: bool = Query(
    default=False,
    title="Sort Descending",
    description="Direction of sort. This defaults to False and causes an ascending sort on the field specified by sort_on. This field is ignored if 'q' is specified an whoosh search is used.",
)


ToolsIndexQueryParam: str = Query(
    default=...,
    title="Search Query",
)

ToolSearchPageQueryParam: int = Query(
    default=1,
    title="Page",
    description="",
)

RepositorySearchPageQueryParam: Optional[int] = Query(
    default=None,
    title="Page",
    description="",
)

RepositorySearchPageSizeQueryParam: int = Query(
    default=10,
    title="Page Size",
)

RepositoryIndexDeletedQueryParam: Optional[bool] = Query(False, title="Deleted?")

RepositoryIndexOwnerQueryParam: Optional[str] = Query(None, title="Owner")

RepositoryIndexNameQueryParam: Optional[str] = Query(None, title="Name")

RepositoryIndexCategoryQueryParam: Optional[str] = Query(None, title="Category ID")

RepositoryIndexToolIdsQueryParam: Optional[List[str]] = Query(
    None, title="Tool IDs", description="List of tool GUIDs to find the repository for"
)


OptionalRepositoryOwnerParam: Optional[str] = Query(None, title="Owner")
OptionalRepositoryNameParam: Optional[str] = Query(None, title="Name")
RequiredRepositoryChangesetRevisionParam: str = Query(..., title="Changeset Revision")
OptionalRepositoryIdParam: Optional[str] = Query(None, title="TSR ID")
OptionalHexlifyParam: Optional[bool] = Query(True, title="Hexlify response")

CategoryIdPathParam: str = Path(
    ..., title="Category ID", description="The encoded database identifier of the category."
)
CategoryRepositoriesInstallableQueryParam: bool = Query(False, title="Installable?")
CategoryRepositoriesSortKeyQueryParam: str = Query("name", title="Sort Key")
CategoryRepositoriesSortOrderQueryParam: str = Query("asc", title="Sort Order")
CategoryRepositoriesPageQueryParam: Optional[int] = Query(None, title="Page")


def ensure_valid_session(trans: SessionRequestContext) -> None:
    """
    Ensure that a valid Galaxy session exists and is available as
    trans.session (part of initialization)
    """
    app = trans.app
    mapping = app.model
    session_manager = GalaxySessionManager(mapping)
    sa_session = app.model.context
    request = trans.request
    # Try to load an existing session
    galaxy_session = None
    prev_galaxy_session = None
    user_for_new_session = None
    invalidate_existing_session = False
    # Track whether the session has changed so we can avoid calling flush
    # in the most common case (session exists and is valid).
    galaxy_session_requires_flush = False
    if secure_id := request.get_cookie(AUTH_COOKIE_NAME):
        session_key: Optional[str] = app.security.decode_guid(secure_id)
        if session_key:
            # We do NOT catch exceptions here, if the database is down the request should fail,
            # and we should not generate a new session.
            galaxy_session = session_manager.get_session_from_session_key(session_key=session_key)
        if not galaxy_session:
            session_key = None

    if galaxy_session is not None and galaxy_session.user is not None and galaxy_session.user.deleted:
        invalidate_existing_session = True
        log.warning(f"User '{galaxy_session.user.email}' is marked deleted, invalidating session")
    # Do we need to invalidate the session for some reason?
    if invalidate_existing_session:
        assert galaxy_session
        prev_galaxy_session = galaxy_session
        prev_galaxy_session.is_valid = False
        galaxy_session = None
    # No relevant cookies, or couldn't find, or invalid, so create a new session
    if galaxy_session is None:
        galaxy_session = create_new_session(trans, prev_galaxy_session, user_for_new_session)
        galaxy_session_requires_flush = True
        trans.set_galaxy_session(galaxy_session)
        set_auth_cookie(trans, galaxy_session)
    else:
        trans.set_galaxy_session(galaxy_session)
    # Do we need to flush the session?
    if galaxy_session_requires_flush:
        sa_session.add(galaxy_session)
        # FIXME: If prev_session is a proper relation this would not
        #        be needed.
        if prev_galaxy_session:
            sa_session.add(prev_galaxy_session)
        sa_session.commit()


def set_auth_cookie(trans: SessionRequestContext, session):
    cookie_name = AUTH_COOKIE_NAME
    set_cookie(trans, trans.app.security.encode_guid(session.session_key), cookie_name)


def set_cookie(trans: SessionRequestContext, value: str, key, path="/", age=90) -> None:
    """Convenience method for setting a session cookie"""
    # In wsgi we were setting both a max_age and and expires, but
    # all browsers support max_age now.
    domain: Optional[str] = trans.app.config.cookie_domain
    trans.response.set_cookie(
        key,
        unicodify(value),
        path=path,
        max_age=3600 * 24 * age,  # 90 days
        httponly=True,
        secure=trans.request.is_secure,
        domain=domain,
    )
