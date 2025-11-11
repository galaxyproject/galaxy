import logging
from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from galaxy.managers.context import ProvidesUserContext
from galaxy.webapps.galaxy.api import DependsOnTrans, Router
from galaxy.managers import users, configuration, workflows
from galaxy import util
from galaxy import web

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
    @router.get("/api/context", summary="Return bootstrapped client context")
    def index(self, request: Request, trans: ProvidesUserContext = DependsOnTrans) -> JSONResponse:
        user_manager = users.UserManager(trans.app)
        user_serializer = users.CurrentUserSerializer(trans.app)
        config_serializer = configuration.ConfigSerializer(trans.app)
        admin_config_serializer = configuration.AdminConfigSerializer(trans.app)

        serializer = admin_config_serializer if user_manager.is_admin(trans.user, trans=trans) else config_serializer
        config = serializer.serialize_to_view(trans.app.config, view="all", host=trans.host)
        config.update(self._get_extended_config(trans))

        js_options = {
            "root": web.url_for("/"),
            "user": user_serializer.serialize(trans.user, USER_KEYS, trans=trans),
            "config": config,
            "session_csrf_token": self._get_csrf_token(trans, request),
        }
        return JSONResponse(js_options)

    def _get_extended_config(self, trans):
        return {
            "active_view": "analysis",
            "enable_webhooks": bool(trans.app.webhooks_registry.webhooks),
            "message_box_visible": trans.app.config.message_box_visible,
            "show_inactivity_warning": trans.app.config.user_activation_on and trans.user and not trans.user.active,
            "tool_dynamic_configs": list(trans.app.toolbox.dynamic_conf_filenames()),
            "sentry": self._get_sentry(trans),
            "stored_workflow_menu_entries":  self._get_workflow_entries(trans),
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
                sentry.email = trans.user.email
        return sentry

    def _get_workflow_entries(self, trans: ProvidesUserContext):
        stored_workflow_menu_index = {}
        stored_workflow_menu_entries = []
        for menu_item in getattr(trans.user, "stored_workflow_menu_entries", []):
            encoded_id = trans.security.encode_id(menu_item.stored_workflow_id)
            if encoded_id not in stored_workflow_menu_index:
                stored_workflow_menu_index[encoded_id] = True
                stored_workflow_menu_entries.append({
                    "id": encoded_id,
                    "name": util.unicodify(menu_item.stored_workflow.name),
                })
        return stored_workflow_menu_entries
