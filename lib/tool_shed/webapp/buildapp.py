"""
Provides factory methods to assemble the Galaxy web application
"""

import atexit
import logging

from paste import httpexceptions

import galaxy.webapps.base.webapp
from galaxy.structured_app import BasicSharedApp
from galaxy.util import asbool
from galaxy.util.properties import load_app_properties
from galaxy.web import url_for
from galaxy.web.framework.middleware.error import ErrorMiddleware
from galaxy.web.framework.middleware.request_id import RequestIDMiddleware
from galaxy.web.framework.middleware.xforwardedhost import XForwardedHostMiddleware
from galaxy.webapps.base.webapp import (
    build_url_map,
    GalaxyWebTransaction,
)
from galaxy.webapps.util import wrap_if_allowed

log = logging.getLogger(__name__)


class ToolShedGalaxyWebTransaction(GalaxyWebTransaction):
    @property
    def repositories_hostname(self) -> str:
        # Use configured tool_shed_url if available
        if tool_shed_url := self.app.config.tool_shed_url:
            return tool_shed_url.rstrip("/")
        # Fall back to request-based URL
        return url_for("/", qualified=True).rstrip("/")

    def get_or_create_default_history(self):
        # tool shed has no concept of histories
        raise NotImplementedError


class CommunityWebApplication(galaxy.webapps.base.webapp.WebApplication):
    injection_aware: bool = True

    def transaction_chooser(self, environ, galaxy_app: BasicSharedApp, session_cookie: str):
        return ToolShedGalaxyWebTransaction(environ, galaxy_app, self, session_cookie)


def add_ui_controllers(webapp, app):
    """Register the HgController — the only remaining WSGI controller."""
    from tool_shed.webapp.controllers.hg import HgController

    webapp.add_ui_controller("hg", HgController(app))


def app_factory(*args, **kwargs):
    """
    Return a wsgi application serving the root object
    """
    return app_pair(*args, **kwargs)[0]


def app_pair(global_conf, load_app_kwds=None, **kwargs):
    """Return a wsgi application serving the root object"""
    # Create the Galaxy tool shed application unless passed in
    load_app_kwds = load_app_kwds or {}
    kwargs = load_app_properties(kwds=kwargs, config_prefix="TOOL_SHED_CONFIG_", **load_app_kwds)
    if "app" in kwargs:
        app = kwargs.pop("app")
        import tool_shed.webapp.app

        tool_shed.webapp.app.app = app
    else:
        try:
            import tool_shed.webapp.app

            app = tool_shed.webapp.app.UniverseApplication(global_conf=global_conf, **kwargs)
            tool_shed.webapp.app.app = app
        except Exception:
            import sys
            import traceback

            traceback.print_exc()
            sys.exit(1)
    atexit.register(app.shutdown)
    # Create the universe WSGI application
    webapp = CommunityWebApplication(app, session_cookie="galaxycommunitysession", name="tool_shed")
    add_ui_controllers(webapp, app)
    # Enable 'hg clone' functionality on repos by letting hgwebapp handle the request
    webapp.add_route("/repos/*path_info", controller="hg", action="handle_request", path_info="/")
    webapp.finalize_config()
    # Wrap the webapp in some useful middleware
    if kwargs.get("middleware", True):
        webapp = wrap_in_middleware(webapp, global_conf, app.application_stack, **kwargs)
    if asbool(kwargs.get("static_enabled", True)):
        webapp = wrap_if_allowed(webapp, app.application_stack, build_url_map, args=(global_conf,), kwargs=kwargs)
    return webapp, app


def wrap_in_middleware(app, global_conf, application_stack, **local_conf):
    """Based on the configuration wrap `app` in a set of common and useful middleware."""
    stack = application_stack
    # Merge the global and local configurations
    conf = global_conf.copy()
    conf.update(local_conf)
    # First put into place httpexceptions, which must be most closely
    # wrapped around the application (it can interact poorly with
    # other middleware):
    app = wrap_if_allowed(app, stack, httpexceptions.make_middleware, name="paste.httpexceptions", args=(conf,))
    assert not asbool(conf.get("use_remote_user", False))

    # Transaction logging (apache access.log style)
    if asbool(conf.get("use_translogger", True)):
        from paste.translogger import TransLogger

        app = wrap_if_allowed(app, stack, TransLogger)

    # X-Forwarded-Host handling
    app = wrap_if_allowed(app, stack, XForwardedHostMiddleware)
    # Request ID handling
    app = wrap_if_allowed(app, stack, RequestIDMiddleware)
    # Error middleware
    app = wrap_if_allowed(app, stack, ErrorMiddleware, args=(conf,))
    return app


