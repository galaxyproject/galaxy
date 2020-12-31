"""
This module *does not* contain API routes. It exclusively contains dependencies to be used in FastAPI routes
"""
from typing import (
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

from galaxy import (
    app as galaxy_app,
    model,
)
from galaxy.app import UniverseApplication
from galaxy.exceptions import AdminRequiredException
from galaxy.managers.jobs import JobManager
from galaxy.managers.session import GalaxySessionManager
from galaxy.managers.users import UserManager
from galaxy.model import User
from galaxy.web.framework.decorators import require_admin_message
from galaxy.work.context import SessionRequestContext


def get_app() -> UniverseApplication:
    return cast(UniverseApplication, galaxy_app.app)


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
                app: UniverseApplication = Depends(get_app),
                galaxysession: Optional[str] = Cookie(None)) -> Optional[model.GalaxySession]:
    if galaxysession:
        session_key = app.security.decode_guid(galaxysession)
        if session_key:
            return session_manager.get_session_from_session_key(session_key)
        # TODO: What should we do if there is no session? Since this is the API, maybe nothing is the right choice?
    return None


def get_api_user(user_manager: UserManager = Depends(get_user_manager), key: Optional[str] = Query(None), x_api_key: Optional[str] = Header(None)) -> Optional[User]:
    api_key = key or x_api_key
    if not api_key:
        return None
    return user_manager.by_api_key(api_key=api_key)


def get_user(galaxy_session: Optional[model.GalaxySession] = Depends(get_session), api_user: Optional[User] = Depends(get_api_user)) -> Optional[User]:
    if galaxy_session:
        return galaxy_session.user
    return api_user


def get_trans(app: UniverseApplication = Depends(get_app), user: Optional[User] = Depends(get_user),
              galaxy_session: Optional[model.GalaxySession] = Depends(get_session),
              ) -> SessionRequestContext:
    app.model.session.expunge_all()
    return SessionRequestContext(app=app, user=user, galaxy_session=galaxy_session)


def get_admin_user(trans: SessionRequestContext = Depends(get_trans)):
    if not trans.user_is_admin:
        raise AdminRequiredException(require_admin_message(trans.app.config, trans.user))
    return trans.user
