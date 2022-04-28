"""
Provides factory methods to assemble the Galaxy web application
"""
import atexit
import logging
import os
from inspect import isclass

from paste import httpexceptions

import galaxy.model
import galaxy.model.mapping
import galaxy.webapps.base.webapp
from galaxy.util import asbool
from galaxy.util.properties import load_app_properties
from galaxy.webapps.base.webapp import build_url_map
from galaxy.webapps.util import wrap_if_allowed

log = logging.getLogger(__name__)


class ReportsWebApplication(galaxy.webapps.base.webapp.WebApplication):
    pass


def add_ui_controllers(webapp, app):
    """
    Search for controllers in the 'galaxy.webapps.controllers' module and add
    them to the webapp.
    """
    import galaxy.webapps.reports.controllers
    from galaxy.webapps.base.controller import BaseUIController

    controller_dir = galaxy.webapps.reports.controllers.__path__[0]
    for fname in os.listdir(controller_dir):
        if not fname.startswith("_") and fname.endswith(".py"):
            name = fname[:-3]
            module_name = f"galaxy.webapps.reports.controllers.{name}"
            module = __import__(module_name)
            for comp in module_name.split(".")[1:]:
                module = getattr(module, comp)
            # Look for a controller inside the modules
            for key in dir(module):
                T = getattr(module, key)
                if isclass(T) and T is not BaseUIController and issubclass(T, BaseUIController):
                    webapp.add_ui_controller(name, T(app))


def app_factory(global_conf, load_app_kwds=None, **kwargs):
    """Return a wsgi application serving the root object"""
    # Create the Galaxy application unless passed in
    load_app_kwds = load_app_kwds or {}
    kwargs = load_app_properties(kwds=kwargs, **load_app_kwds)
    if "app" in kwargs:
        app = kwargs.pop("app")
    else:
        from galaxy.webapps.reports.app import UniverseApplication

        app = UniverseApplication(global_conf=global_conf, **kwargs)
    atexit.register(app.shutdown)
    # Create the universe WSGI application
    webapp = ReportsWebApplication(app, session_cookie="galaxyreportssession", name="reports")
    add_ui_controllers(webapp, app)
    # These two routes handle our simple needs at the moment
    webapp.add_route("/{controller}/{action}", controller="root", action="index")
    webapp.add_route("/{action}", controller="root", action="index")
    webapp.finalize_config()
    # Wrap the webapp in some useful middleware
    if kwargs.get("middleware", True):
        webapp = wrap_in_middleware(webapp, global_conf, app.application_stack, **kwargs)
    if asbool(kwargs.get("static_enabled", True)):
        webapp = wrap_if_allowed(webapp, app.application_stack, build_url_map, args=(global_conf,), kwargs=kwargs)
    return webapp


def wrap_in_middleware(app, global_conf, application_stack, **local_conf):
    """Based on the configuration wrap `app` in a set of common and useful middleware."""
    stack = application_stack
    # Merge the global and local configurations
    conf = global_conf.copy()
    conf.update(local_conf)
    debug = asbool(conf.get("debug", False))
    # First put into place httpexceptions, which must be most closely
    # wrapped around the application (it can interact poorly with
    # other middleware):
    app = wrap_if_allowed(app, stack, httpexceptions.make_middleware, name="paste.httpexceptions", args=(conf,))
    # The recursive middleware allows for including requests in other
    # requests or forwarding of requests, all on the server side.
    if asbool(conf.get("use_recursive", True)):
        from paste import recursive

        app = wrap_if_allowed(app, stack, recursive.RecursiveMiddleware, args=(conf,))
    # Various debug middleware that can only be turned on if the debug
    # flag is set, either because they are insecure or greatly hurt
    # performance
    if debug:
        # Middleware to check for WSGI compliance
        if asbool(conf.get("use_lint", True)):
            from paste import lint

            app = wrap_if_allowed(app, stack, lint.make_middleware, name="paste.lint", args=(conf,))
        # Middleware to run the python profiler on each request
        if asbool(conf.get("use_profile", False)):
            import profile

            app = wrap_if_allowed(app, stack, profile.ProfileMiddleware, args=(conf,))
        # Middleware that intercepts print statements and shows them on the
        # returned page
        if asbool(conf.get("use_printdebug", True)):
            from paste.debug import prints

            app = wrap_if_allowed(app, stack, prints.PrintDebugMiddleware, args=(conf,))
    # Error middleware
    import galaxy.web.framework.middleware.error

    app = wrap_if_allowed(app, stack, galaxy.web.framework.middleware.error.ErrorMiddleware, args=(conf,))
    # Transaction logging (apache access.log style)
    if asbool(conf.get("use_translogger", True)):
        from paste.translogger import TransLogger

        app = wrap_if_allowed(app, stack, TransLogger)
    # X-Forwarded-Host handling
    from galaxy.web.framework.middleware.xforwardedhost import XForwardedHostMiddleware

    app = wrap_if_allowed(app, stack, XForwardedHostMiddleware)
    return app
