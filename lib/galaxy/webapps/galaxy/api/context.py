import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from galaxy import (
    util,
    web,
)
from galaxy.managers.configuration import ConfigurationManager
from galaxy.managers.users import CurrentUserSerializer
from galaxy.managers.context import ProvidesUserContext
from galaxy.schema import SerializationParams
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["context"])

USER_KEYS = (
    "id",
    "email",
    "username",
    "is_admin",
    "total_disk_usage",
    "nice_total_disk_usage",
    "quota_percent",
    "preferences",
)


@router.cbv
class FastAPIContext:
    configuration_manager: ConfigurationManager = depends(ConfigurationManager)
    user_serializer: CurrentUserSerializer = depends(CurrentUserSerializer)

    @router.get("/context", summary="Return bootstrapped client context")
    def index(self, request: Request, trans: ProvidesUserContext = DependsOnTrans) -> JSONResponse:
        config = self.configuration_manager.get_configuration(trans, SerializationParams(view="all"))
        config.update(self._get_extended_config(trans))
        js_options = {
            "root": web.url_for("/"),
            "user": self.user_serializer.serialize(trans.user, USER_KEYS, trans=trans),
            "config": config,
            "session_csrf_token": self._get_csrf_token(trans, request),
        }
        return JSONResponse(js_options)

    def _get_extended_config(self, trans):
        return {
            "enable_webhooks": bool(trans.app.webhooks_registry.webhooks),
            "show_inactivity_warning": trans.app.config.user_activation_on and trans.user and not trans.user.active,
            "sentry": self._get_sentry(trans),
            "stored_workflow_menu_entries": self._get_workflow_entries(trans),
        }

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

    def _get_sentry(self, trans: ProvidesUserContext):
        sentry = {}
        if trans.app.config.sentry_dsn:
            sentry["sentry_dsn_public"] = trans.app.config.sentry_dsn_public
            if trans.user:
                sentry["email"] = trans.user.email
        return sentry

    def _get_workflow_entries(self, trans: ProvidesUserContext):
        stored_workflow_menu_index = {}
        stored_workflow_menu_entries = []
        for menu_item in getattr(trans.user, "stored_workflow_menu_entries", []):
            encoded_id = trans.security.encode_id(menu_item.stored_workflow_id)
            if encoded_id not in stored_workflow_menu_index:
                stored_workflow_menu_index[encoded_id] = True
                stored_workflow_menu_entries.append(
                    {
                        "id": encoded_id,
                        "name": util.unicodify(menu_item.stored_workflow.name),
                    }
                )
        return stored_workflow_menu_entries
