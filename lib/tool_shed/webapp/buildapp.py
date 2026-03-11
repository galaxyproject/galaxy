"""
Provides factory methods to assemble the Galaxy web application
"""

import atexit
import logging
import os
from inspect import isclass
from urllib.parse import parse_qs

import routes
from paste import httpexceptions
from routes.middleware import RoutesMiddleware

import galaxy.webapps.base.webapp
from galaxy import util
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
    """
    Search for controllers in the 'galaxy.webapps.controllers' module and add
    them to the webapp.
    """
    import tool_shed.webapp.controllers
    from galaxy.webapps.base.controller import BaseUIController

    controller_dir = tool_shed.webapp.controllers.__path__[0]
    for fname in os.listdir(controller_dir):
        if not fname.startswith("_") and fname.endswith(".py"):
            name = fname[:-3]
            module_name = f"tool_shed.webapp.controllers.{name}"
            module = __import__(module_name)
            for comp in module_name.split(".")[1:]:
                module = getattr(module, comp)
            # Look for a controller inside the modules
            for key in dir(module):
                T = getattr(module, key)
                if isclass(T) and T is not BaseUIController and issubclass(T, BaseUIController):
                    webapp.add_ui_controller(name, T(app))


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
    # Handle displaying tool help images and README file images for tools contained in repositories.
    webapp.add_route(
        "/repository/static/images/{repository_id}/{image_file:.+?}",
        controller="repository",
        action="display_image_in_repository",
        repository_id=None,
        image_file=None,
    )
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
    # Create a separate mapper for redirects to prevent conflicts.
    redirect_mapper = routes.Mapper()
    redirect_mapper = _map_redirects(redirect_mapper)
    # Load the Routes middleware which we use for redirecting
    app = wrap_if_allowed(app, stack, RoutesMiddleware, args=(redirect_mapper,))
    # If we're using remote_user authentication, add middleware that
    # protects Galaxy from improperly configured authentication in the
    # upstream server
    if asbool(conf.get("use_remote_user", False)):
        from tool_shed.webapp.framework.middleware.remoteuser import RemoteUser

        app = wrap_if_allowed(
            app,
            stack,
            RemoteUser,
            kwargs=dict(
                maildomain=conf.get("remote_user_maildomain", None),
                display_servers=util.listify(conf.get("display_servers", "")),
                admin_users=conf.get("admin_users", "").split(","),
                remote_user_header=conf.get("remote_user_header", "HTTP_REMOTE_USER"),
                remote_user_secret_header=conf.get("remote_user_secret", None),
                normalize_remote_user_email=conf.get("normalize_remote_user_email", False),
            ),
        )

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


def _map_redirects(mapper):
    """
    Add redirect to the Routes mapper and forward the received query string.
    Subsequently when the redirect is triggered in Routes middleware the request
    will not even reach the webapp.
    """

    def forward_qs(environ, result):
        qs_dict = parse_qs(environ["QUERY_STRING"])
        for qs in qs_dict:
            result[qs] = qs_dict[qs]
        return True

    mapper.redirect(
        "/repository/status_for_installed_repository",
        "/api/repositories/updates/",
        _redirect_code="301 Moved Permanently",
        conditions=dict(function=forward_qs),
    )
    return mapper
