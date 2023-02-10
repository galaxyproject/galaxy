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
from galaxy.util import asbool
from galaxy.util.properties import load_app_properties
from galaxy.webapps.base.webapp import build_url_map
from galaxy.webapps.util import wrap_if_allowed

log = logging.getLogger(__name__)


class CommunityWebApplication(galaxy.webapps.base.webapp.WebApplication):
    pass


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
    else:
        try:
            from tool_shed.webapp.app import UniverseApplication

            app = UniverseApplication(global_conf=global_conf, **kwargs)
        except Exception:
            import sys
            import traceback

            traceback.print_exc()
            sys.exit(1)
    atexit.register(app.shutdown)
    # Create the universe WSGI application
    webapp = CommunityWebApplication(app, session_cookie="galaxycommunitysession", name="tool_shed")
    add_ui_controllers(webapp, app)
    webapp.add_route("/view/{owner}", controller="repository", action="sharable_owner")
    webapp.add_route("/view/{owner}/{name}", controller="repository", action="sharable_repository")
    webapp.add_route(
        "/view/{owner}/{name}/{changeset_revision}", controller="repository", action="sharable_repository_revision"
    )
    # Handle displaying tool help images and README file images for tools contained in repositories.
    webapp.add_route(
        "/repository/static/images/{repository_id}/{image_file:.+?}",
        controller="repository",
        action="display_image_in_repository",
        repository_id=None,
        image_file=None,
    )
    webapp.add_route("/{controller}/{action}", action="index")
    webapp.add_route("/{action}", controller="repository", action="index")
    # Enable 'hg clone' functionality on repos by letting hgwebapp handle the request
    webapp.add_route("/repos/*path_info", controller="hg", action="handle_request", path_info="/")
    # Add the web API.  # A good resource for RESTful services - https://routes.readthedocs.io/en/latest/restful.html
    webapp.add_api_controllers("tool_shed.webapp.api", app)
    webapp.mapper.connect(
        "api_key_retrieval",
        "/api/authenticate/baseauth/",
        controller="authenticate",
        action="get_tool_shed_api_key",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect("group", "/api/groups/", controller="groups", action="index", conditions=dict(method=["GET"]))
    webapp.mapper.connect(
        "group", "/api/groups/", controller="groups", action="create", conditions=dict(method=["POST"])
    )
    webapp.mapper.connect(
        "group", "/api/groups/{encoded_id}", controller="groups", action="show", conditions=dict(method=["GET"])
    )
    webapp.mapper.resource(
        "category",
        "categories",
        controller="categories",
        name_prefix="category_",
        path_prefix="/api",
        parent_resources=dict(member_name="category", collection_name="categories"),
    )
    webapp.mapper.connect(
        "repositories_in_category",
        "/api/categories/{category_id}/repositories",
        controller="categories",
        action="get_repositories",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "show_updates_for_repository",
        "/api/repositories/updates",
        controller="repositories",
        action="updates",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.resource(
        "repository",
        "repositories",
        controller="repositories",
        collection={
            "add_repository_registry_entry": "POST",
            "get_repository_revision_install_info": "GET",
            "get_ordered_installable_revisions": "GET",
            "get_installable_revisions": "GET",
            "remove_repository_registry_entry": "POST",
            "repository_ids_for_setting_metadata": "GET",
            "reset_metadata_on_repositories": "POST",
            "reset_metadata_on_repository": "POST",
        },
        name_prefix="repository_",
        path_prefix="/api",
        parent_resources=dict(member_name="repository", collection_name="repositories"),
    )
    webapp.mapper.resource(
        "repository_revision",
        "repository_revisions",
        member={"repository_dependencies": "GET", "export": "POST"},
        controller="repository_revisions",
        name_prefix="repository_revision_",
        path_prefix="/api",
        parent_resources=dict(member_name="repository_revision", collection_name="repository_revisions"),
    )
    webapp.mapper.resource(
        "user",
        "users",
        controller="users",
        name_prefix="user_",
        path_prefix="/api",
        parent_resources=dict(member_name="user", collection_name="users"),
    )
    webapp.mapper.connect(
        "update_repository",
        "/api/repositories/{id}",
        controller="repositories",
        action="update",
        conditions=dict(method=["PATCH", "PUT"]),
    )
    webapp.mapper.connect(
        "repository_create_changeset_revision",
        "/api/repositories/{id}/changeset_revision",
        controller="repositories",
        action="create_changeset_revision",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect(
        "repository_get_metadata",
        "/api/repositories/{id}/metadata",
        controller="repositories",
        action="metadata",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "repository_show_tools",
        "/api/repositories/{id}/{changeset}/show_tools",
        controller="repositories",
        action="show_tools",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "create_repository",
        "/api/repositories",
        controller="repositories",
        action="create",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect("tools", "/api/tools", controller="tools", action="index", conditions=dict(method=["GET"]))
    webapp.mapper.connect("json", "/api/tools/json", controller="tools", action="json", conditions=dict(method=["GET"]))
    webapp.mapper.connect(
        "version", "/api/version", controller="configuration", action="version", conditions=dict(method=["GET"])
    )

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
    debug = asbool(conf.get("debug", False))
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
    # The recursive middleware allows for including requests in other
    # requests or forwarding of requests, all on the server side.
    if asbool(conf.get("use_recursive", True)):
        from paste import recursive

        app = wrap_if_allowed(app, stack, recursive.RecursiveMiddleware, args=(conf,))
    # Transaction logging (apache access.log style)
    if asbool(conf.get("use_translogger", True)):
        from paste.translogger import TransLogger

        app = wrap_if_allowed(app, stack, TransLogger)

    # X-Forwarded-Host handling
    from galaxy.web.framework.middleware.xforwardedhost import XForwardedHostMiddleware

    app = wrap_if_allowed(app, stack, XForwardedHostMiddleware)
    # Various debug middleware that can only be turned on if the debug
    # flag is set, either because they are insecure or greatly hurt
    # performance.
    if debug:
        # Middleware to check for WSGI compliance
        if asbool(conf.get("use_lint", True)):
            from paste import lint

            app = wrap_if_allowed(app, stack, lint.make_middleware, name="paste.lint", args=(conf,))
        # Middleware to run the python profiler on each request
        if asbool(conf.get("use_profile", False)):
            from paste.debug import profile

            app = wrap_if_allowed(app, stack, profile.ProfileMiddleware, args=(conf,))
    # Error middleware
    import galaxy.web.framework.middleware.error

    app = wrap_if_allowed(app, stack, galaxy.web.framework.middleware.error.ErrorMiddleware, args=(conf,))
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
