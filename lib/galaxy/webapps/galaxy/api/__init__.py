"""
This module *does not* contain API routes. It exclusively contains dependencies to be used in FastAPI routes
"""
from functools import lru_cache
from typing import (
    Optional,
)

from fastapi import (
    Cookie,
    Depends,
    Header,
    HTTPException,
    Query,
)
from sqlalchemy.orm import Session

from galaxy import (
    app as galaxy_app,
    exceptions,
    model,
)
from galaxy.app import UniverseApplication
from galaxy.managers.session import GalaxySessionManager
from galaxy.managers.users import UserManager
from galaxy.model import User
from galaxy.work.context import SessionRequestContext


@lru_cache()
def get_app() -> UniverseApplication:
    return galaxy_app.app


@lru_cache()
def get_db(app: UniverseApplication = Depends(get_app)) -> Session:
    # TODO: return sqlachemy 2.0 style session without autocommit and expire_on_commit!
    return app.model.session


@lru_cache()
def get_user_manager(app: UniverseApplication = Depends(get_app)):
    return UserManager(app)


@lru_cache()
def get_session_manager(app=Depends(get_app)) -> GalaxySessionManager:
    # TODO: find out how to adapt dependency for Galaxy/Report/TS
    return GalaxySessionManager(app.model)


@lru_cache()
def get_session(session_manager: GalaxySessionManager = Depends(get_session_manager),
                app: UniverseApplication = Depends(get_app),
                galaxysession: Optional[str] = Cookie(None)) -> Optional[model.GalaxySession]:
    if galaxysession:
        session_key = app.security.decode_guid(galaxysession)
        if session_key:
            return session_manager.get_session_from_session_key(session_key)
        # TODO: What should we do if there is no session? Since this is the API, maybe nothing is the right choice?


@lru_cache()
def get_api_user(user_manager: UserManager = Depends(get_user_manager), key: Optional[str] = Query(None), x_api_key: Optional[str] = Header(None)) -> Optional[User]:
    api_key = key or x_api_key
    if not api_key:
        return None
    try:
        return user_manager.by_api_key(api_key=api_key)
    except exceptions.AuthenticationFailed as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@lru_cache()
def get_user(galaxy_session: Optional[model.GalaxySession] = Depends(get_session), api_user: Optional[User] = Depends(get_api_user)) -> Optional[User]:
    if galaxy_session:
        return galaxy_session.user
    return api_user


@lru_cache()
def get_trans(app=Depends(get_app), user: Optional[User] = Depends(get_user),
              galaxy_session: Optional[model.GalaxySession] = Depends(get_session),
              ) -> SessionRequestContext:
    return SessionRequestContext(app=app, user=user, galaxy_session=galaxy_session)


@lru_cache()
def get_admin_user(trans: SessionRequestContext = Depends(get_trans), user_manager: UserManager = Depends(get_user_manager)):
    if user_manager.is_admin(trans.user):
        return trans.user
    else:
        raise HTTPException(status_code=403, detail="You must be an administrator to access this feature.")
