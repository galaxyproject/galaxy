import logging
from typing import (
    Any,
    Optional,
)

from fastapi import Request

from galaxy import web
from galaxy.managers.configuration import ConfigurationManager
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.users import CurrentUserSerializer
from galaxy.schema import SerializationParams
from galaxy.schema.schema import Model
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["context"])


class ContextResponse(Model):
    root: str
    config: dict[str, Any]
    session_csrf_token: Optional[str] = None
    user: dict[str, Any]


@router.cbv
class FastAPIContext:
    configuration_manager: ConfigurationManager = depends(ConfigurationManager)
    user_serializer: CurrentUserSerializer = depends(CurrentUserSerializer)

    @router.get("/context", summary="Return bootstrapped client context")
    def index(self, request: Request, trans: ProvidesUserContext = DependsOnTrans) -> ContextResponse:
        config = self.configuration_manager.get_configuration(trans, SerializationParams(view="all"))
        return ContextResponse(
            config=config,
            root=web.url_for("/"),
            session_csrf_token=self._get_csrf_token(trans, request),
            user=self.user_serializer.serialize_to_view(trans.user, "detailed"),
        )

    def _get_csrf_token(self, trans: ProvidesUserContext, request: Request):
        cookie = request.cookies.get("galaxysession")
        if not cookie:
            return None
        try:
            session_key = trans.app.security.decode_guid(cookie)
            session = (
                trans.sa_session.query(trans.app.model.GalaxySession)
                .filter_by(session_key=session_key, is_valid=True)
                .first()
            )
            if session:
                return trans.app.security.encode_id(session.id, kind="csrf")
        except Exception:
            log.debug("Failed to derive CSRF token", exc_info=True)
        return None
