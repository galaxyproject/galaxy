"""
This module *does not* contain API routes. It exclusively contains dependencies to be used in FastAPI routes
"""
from typing import (
    AsyncGenerator,
    cast,
    Optional,
)

from fastapi import (
    Cookie,
    Depends,
    Header,
    Query,
)
from sqlalchemy.orm import Session
try:
    from starlette_context import context as request_context
except ImportError:
    request_context = None

from galaxy import (
    app as galaxy_app,
    model,
)
from galaxy.app import UniverseApplication
from galaxy.exceptions import (
    AdminRequiredException,
    UserCannotRunAsException,
    UserInvalidRunAsException,
)
from galaxy.managers.jobs import JobManager
from galaxy.managers.session import GalaxySessionManager
from galaxy.managers.users import UserManager
from galaxy.model import User
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.web.framework.decorators import require_admin_message
from galaxy.work.context import SessionRequestContext


async def _get_app() -> AsyncGenerator[UniverseApplication, None]:
    app = cast(UniverseApplication, galaxy_app.app)
    request_id = request_context.data['X-Request-ID']
    app.model.set_request_id(request_id)
    try:
        yield app
    finally:
        app.model.unset_request_id(request_id)


async def get_app(app=Depends(_get_app)) -> UniverseApplication:
    return app


def get_id_encoding_helper(app: UniverseApplication = Depends(get_app)) -> IdEncodingHelper:
    return app.security


def get_job_manager(app: UniverseApplication = Depends(get_app)) -> JobManager:
    return JobManager(app=app)


def get_db(app: UniverseApplication = Depends(get_app)) -> Session:
    # TODO: return sqlachemy 2.0 style session without autocommit and expire_on_commit!
    return app.model.session


def get_user_manager(app: UniverseApplication = Depends(get_app)) -> UserManager:
    return UserManager(app)


def get_session_manager(app: UniverseApplication = Depends(get_app)) -> GalaxySessionManager:
    # TODO: find out how to adapt dependency for Galaxy/Report/TS
    return GalaxySessionManager(app.model)


def get_session(session_manager: GalaxySessionManager = Depends(get_session_manager),
                security: IdEncodingHelper = Depends(get_id_encoding_helper),
                galaxysession: Optional[str] = Cookie(None)) -> Optional[model.GalaxySession]:
    if galaxysession:
        session_key = security.decode_guid(galaxysession)
        if session_key:
            return session_manager.get_session_from_session_key(session_key)
        # TODO: What should we do if there is no session? Since this is the API, maybe nothing is the right choice?
    return None


def get_api_user(
        security: IdEncodingHelper = Depends(get_id_encoding_helper),
        user_manager: UserManager = Depends(get_user_manager),
        key: Optional[str] = Query(None),
        x_api_key: Optional[str] = Header(None),
        run_as: Optional[EncodedDatabaseIdField] = Header(None, title='Run as User', description='Admins and ')) -> Optional[User]:
    api_key = key or x_api_key
    if not api_key:
        return None
    user = user_manager.by_api_key(api_key=api_key)
    if run_as:
        if user_manager.user_can_do_run_as(user):
            try:
                decoded_run_as_id = security.decode_id(run_as)
            except Exception:
                raise UserInvalidRunAsException
            return user_manager.by_id(decoded_run_as_id)
        else:
            raise UserCannotRunAsException
    return user


def get_user(galaxy_session: Optional[model.GalaxySession] = Depends(get_session), api_user: Optional[User] = Depends(get_api_user)) -> Optional[User]:
    if galaxy_session:
        return galaxy_session.user
    return api_user


def get_trans(app: UniverseApplication = Depends(get_app), user: Optional[User] = Depends(get_user),
              galaxy_session: Optional[model.GalaxySession] = Depends(get_session),
              ) -> SessionRequestContext:
    return SessionRequestContext(app=app, user=user, galaxy_session=galaxy_session)


def get_admin_user(trans: SessionRequestContext = Depends(get_trans)):
    if not trans.user_is_admin:
        raise AdminRequiredException(require_admin_message(trans.app.config, trans.user))
    return trans.user
