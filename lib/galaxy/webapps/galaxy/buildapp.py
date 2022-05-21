"""
Provides factory methods to assemble the Galaxy web application
"""
import atexit
import logging
import sys
import threading
import traceback
from urllib.parse import urljoin

from paste import httpexceptions
from tuswsgi import TusMiddleware

import galaxy.app
import galaxy.datatypes.registry
import galaxy.model
import galaxy.model.mapping
import galaxy.web.framework
import galaxy.webapps.base.webapp
from galaxy import util
from galaxy.security.validate_user_input import VALID_PUBLICNAME_RE
from galaxy.util import asbool
from galaxy.util.properties import load_app_properties
from galaxy.web.framework.middleware.error import ErrorMiddleware
from galaxy.web.framework.middleware.request_id import RequestIDMiddleware
from galaxy.web.framework.middleware.xforwardedhost import XForwardedHostMiddleware
from galaxy.webapps.base.webapp import build_url_map
from galaxy.webapps.util import wrap_if_allowed

log = logging.getLogger(__name__)


class GalaxyWebApplication(galaxy.webapps.base.webapp.WebApplication):
    injection_aware = True


def app_factory(*args, **kwargs):
    """
    Return a wsgi application serving the root object
    """
    return app_pair(*args, **kwargs)[0]


def app_pair(global_conf, load_app_kwds=None, wsgi_preflight=True, **kwargs):
    """
    Return a wsgi application serving the root object and the Galaxy application.

    When creating an app for asgi, set wsgi_preflight to False to allow FastAPI
    middleware to handle CORS options, etc..
    """
    load_app_kwds = load_app_kwds or {}
    kwargs = load_app_properties(kwds=kwargs, **load_app_kwds)
    # Create the Galaxy application unless passed in
    if "app" in kwargs:
        app = kwargs.pop("app")
        galaxy.app.app = app
    else:
        try:
            app = galaxy.app.UniverseApplication(global_conf=global_conf, **kwargs)
            galaxy.app.app = app
        except Exception:
            traceback.print_exc()
            sys.exit(1)

    if kwargs.get("register_shutdown_at_exit", True):
        # Call app's shutdown method when the interpeter exits, this cleanly stops
        # the various Galaxy application daemon threads
        app.application_stack.register_postfork_function(atexit.register, app.shutdown)
    # Create the universe WSGI application
    webapp = GalaxyWebApplication(app, session_cookie="galaxysession", name="galaxy")

    # STANDARD CONTROLLER ROUTES
    webapp.add_ui_controllers("galaxy.webapps.galaxy.controllers", app)
    # Force /history to go to view of current
    webapp.add_route("/history", controller="history", action="view")
    webapp.add_route("/history/view/{id}", controller="history", action="view")

    # Force /activate to go to the controller
    webapp.add_route("/activate", controller="user", action="activate")

    # Authentication endpoints.
    webapp.add_route("/authnz/", controller="authnz", action="index", provider=None)
    webapp.add_route("/authnz/{provider}/login", controller="authnz", action="login", provider=None)
    webapp.add_route("/authnz/{provider}/callback", controller="authnz", action="callback", provider=None)
    webapp.add_route(
        "/authnz/{provider}/disconnect/{email}", controller="authnz", action="disconnect", provider=None, email=None
    )
    webapp.add_route("/authnz/{provider}/logout", controller="authnz", action="logout", provider=None)
    webapp.add_route("/authnz/{provider}/create_user", controller="authnz", action="create_user")
    # Returns the provider specific logout url for currently logged in provider
    webapp.add_route("/authnz/logout", controller="authnz", action="get_logout_url")
    webapp.add_route("/authnz/get_cilogon_idps", controller="authnz", action="get_cilogon_idps")

    # These two routes handle our simple needs at the moment
    webapp.add_route(
        "/async/{tool_id}/{data_id}/{data_secret}",
        controller="async",
        action="index",
        tool_id=None,
        data_id=None,
        data_secret=None,
    )
    webapp.add_route("/{controller}/{action}", action="index")
    webapp.add_route("/{action}", controller="root", action="index")

    # allow for subdirectories in extra_files_path
    webapp.add_route(
        "/datasets/{dataset_id}/display/{filename:.+?}",
        controller="dataset",
        action="display",
        dataset_id=None,
        filename=None,
    )
    webapp.add_route(
        "/datasets/{dataset_id}/{action}/{filename}",
        controller="dataset",
        action="index",
        dataset_id=None,
        filename=None,
    )
    webapp.add_route(
        "/display_application/{dataset_id}/{app_name}/{link_name}/{user_id}/{app_action}/{action_param}/{action_param_extra:.+?}",
        controller="dataset",
        action="display_application",
        dataset_id=None,
        user_id=None,
        app_name=None,
        link_name=None,
        app_action=None,
        action_param=None,
        action_param_extra=None,
    )

    USERNAME_REQS = {"username": VALID_PUBLICNAME_RE.pattern.strip("^$")}
    webapp.add_route(
        "/u/{username}/d/{slug}/{filename}",
        controller="dataset",
        action="display_by_username_and_slug",
        filename=None,
        requirements=USERNAME_REQS,
    )
    webapp.add_route(
        "/u/{username}/p/{slug}", controller="page", action="display_by_username_and_slug", requirements=USERNAME_REQS
    )
    webapp.add_route(
        "/u/{username}/h/{slug}",
        controller="history",
        action="display_by_username_and_slug",
        requirements=USERNAME_REQS,
    )
    webapp.add_route(
        "/u/{username}/w/{slug}",
        controller="workflow",
        action="display_by_username_and_slug",
        requirements=USERNAME_REQS,
    )
    webapp.add_route(
        "/u/{username}/w/{slug}/{format}",
        controller="workflow",
        action="display_by_username_and_slug",
        requirements=USERNAME_REQS,
    )
    webapp.add_route(
        "/u/{username}/v/{slug}",
        controller="visualization",
        action="display_by_username_and_slug",
        requirements=USERNAME_REQS,
    )

    # TODO: Refactor above routes into external method to allow testing in
    # isolation as well.
    populate_api_routes(webapp, app)
    if wsgi_preflight:
        # API OPTIONS RESPONSE
        webapp.mapper.connect(
            "options",
            "/api/{path_info:.*?}",
            controller="authenticate",
            action="options",
            conditions={"method": ["OPTIONS"]},
        )

    # CLIENTSIDE ROUTES
    # The following are routes that are handled completely on the clientside.
    # The following routes don't bootstrap any information, simply provide the
    # base analysis interface at which point the application takes over.

    webapp.add_client_route("/admin/data_tables", "admin")
    webapp.add_client_route("/admin/data_types", "admin")
    webapp.add_client_route("/admin/jobs", "admin")
    webapp.add_client_route("/admin/invocations", "admin")
    webapp.add_client_route("/admin/toolbox_dependencies", "admin")
    webapp.add_client_route("/admin/data_manager{path_info:.*}", "admin")
    webapp.add_client_route("/admin/error_stack", "admin")
    webapp.add_client_route("/admin/users", "admin")
    webapp.add_client_route("/admin/users/create", "admin")
    webapp.add_client_route("/admin/display_applications", "admin")
    webapp.add_client_route("/admin/reset_metadata", "admin")
    webapp.add_client_route("/admin/roles", "admin")
    webapp.add_client_route("/admin/forms", "admin")
    webapp.add_client_route("/admin/groups", "admin")
    webapp.add_client_route("/admin/repositories", "admin")
    webapp.add_client_route("/admin/sanitize_allow", "admin")
    webapp.add_client_route("/admin/tool_versions", "admin")
    webapp.add_client_route("/admin/toolshed", "admin")
    webapp.add_client_route("/admin/quotas", "admin")
    webapp.add_client_route("/admin/form/{form_id}", "admin")
    webapp.add_client_route("/admin/api_keys", "admin")
    webapp.add_client_route("/login/confirm")
    webapp.add_client_route("/tools/view")
    webapp.add_client_route("/tools/json")
    webapp.add_client_route("/tours")
    webapp.add_client_route("/tours/{tour_id}")
    webapp.add_client_route("/user")
    webapp.add_client_route("/user/{form_id}")
    webapp.add_client_route("/welcome/new")
    webapp.add_client_route("/visualizations")
    webapp.add_client_route("/visualizations/edit")
    webapp.add_client_route("/visualizations/sharing")
    webapp.add_client_route("/visualizations/list_published")
    webapp.add_client_route("/visualizations/list")
    webapp.add_client_route("/pages/list")
    webapp.add_client_route("/pages/list_published")
    webapp.add_client_route("/pages/create")
    webapp.add_client_route("/pages/edit")
    webapp.add_client_route("/pages/sharing")
    webapp.add_client_route("/histories/citations")
    webapp.add_client_route("/histories/list")
    webapp.add_client_route("/histories/import")
    webapp.add_client_route("/histories/{history_id}/export")
    webapp.add_client_route("/histories/list_published")
    webapp.add_client_route("/histories/list_shared")
    webapp.add_client_route("/histories/rename")
    webapp.add_client_route("/histories/sharing")
    webapp.add_client_route("/histories/permissions")
    webapp.add_client_route("/histories/view")
    webapp.add_client_route("/histories/show_structure")
    webapp.add_client_route("/datasets/list")
    webapp.add_client_route("/datasets/edit")
    webapp.add_client_route("/collection/edit/{collection_id}")
    webapp.add_client_route("/datasets/error")
    webapp.add_client_route("/jobs/{job_id}/view")
    webapp.add_client_route("/datasets/{dataset_id}/details")
    webapp.add_client_route("/datasets/{dataset_id}/show_params")
    webapp.add_client_route("/workflows/list")
    webapp.add_client_route("/workflows/list_published")
    webapp.add_client_route("/workflows/create")
    webapp.add_client_route("/workflows/run")
    webapp.add_client_route("/workflows/import")
    webapp.add_client_route("/workflows/trs_import")
    webapp.add_client_route("/workflows/trs_search")
    webapp.add_client_route("/workflows/invocations")
    webapp.add_client_route("/workflows/sharing")
    webapp.add_client_route("/workflows/{stored_workflow_id}/invocations")
    webapp.add_client_route("/workflows/invocations/report")
    # webapp.add_client_route('/workflows/invocations/view_bco')
    webapp.add_client_route("/custom_builds")
    webapp.add_client_route("/interactivetool_entry_points/list")
    webapp.add_client_route("/libraries{path:.*?}")
    webapp.add_client_route("/storage{path:.*?}")

    # ==== Done
    # Indicate that all configuration settings have been provided
    webapp.finalize_config()
    app.api_spec = webapp.build_apispec()

    # Wrap the webapp in some useful middleware
    if kwargs.get("middleware", True):
        webapp = wrap_in_middleware(webapp, global_conf, app.application_stack, **kwargs)
    if asbool(kwargs.get("static_enabled", True)):
        webapp = wrap_if_allowed(webapp, app.application_stack, build_url_map, args=(global_conf,), kwargs=kwargs)
    app.application_stack.register_postfork_function(postfork_setup)

    for th in threading.enumerate():
        if th.is_alive():
            log.debug("Prior to webapp return, Galaxy thread %s is alive.", th)
    # Return
    return webapp, app


def postfork_setup():
    from galaxy.app import app

    app.application_stack.log_startup()


def populate_api_routes(webapp, app):
    webapp.add_api_controllers("galaxy.webapps.galaxy.api", app)

    _add_item_tags_controller(
        webapp, name_prefix="history_content_", path_prefix="/api/histories/{history_id}/contents/{history_content_id}"
    )
    webapp.mapper.connect(
        "cloud_storage", "/api/cloud/storage/", controller="cloud", action="index", conditions=dict(method=["GET"])
    )
    webapp.mapper.connect(
        "cloud_storage_get",
        "/api/cloud/storage/get",
        controller="cloud",
        action="get",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect(
        "cloud_storage_send",
        "/api/cloud/storage/send",
        controller="cloud",
        action="send",
        conditions=dict(method=["POST"]),
    )

    _add_item_tags_controller(webapp, name_prefix="history_", path_prefix="/api/histories/{history_id}")
    _add_item_tags_controller(webapp, name_prefix="workflow_", path_prefix="/api/workflows/{workflow_id}")
    _add_item_annotation_controller(
        webapp, name_prefix="history_content_", path_prefix="/api/histories/{history_id}/contents/{history_content_id}"
    )
    _add_item_annotation_controller(webapp, name_prefix="history_", path_prefix="/api/histories/{history_id}")
    _add_item_annotation_controller(webapp, name_prefix="workflow_", path_prefix="/api/workflows/{workflow_id}")
    _add_item_provenance_controller(
        webapp, name_prefix="history_content_", path_prefix="/api/histories/{history_id}/contents/{history_content_id}"
    )

    webapp.mapper.resource("form", "forms", path_prefix="/api")
    webapp.mapper.resource("upload", "uploads", path_prefix="/api")
    webapp.mapper.connect(
        "/api/upload/resumable_upload/{session_id}",
        controller="uploads",
        action="hooks",
        conditions=dict(method=["PATCH"]),
    )
    webapp.mapper.connect("/api/upload/resumable_upload", controller="uploads", action="hooks")
    webapp.mapper.connect("/api/upload/hooks", controller="uploads", action="hooks", conditions=dict(method=["POST"]))
    webapp.mapper.resource(
        "revision",
        "revisions",
        path_prefix="/api/pages/{page_id}",
        controller="page_revisions",
        parent_resources=dict(member_name="page", collection_name="pages"),
    )
    webapp.mapper.resource("group", "groups", path_prefix="/api")

    webapp.mapper.connect("/api/cloud/authz/", action="index", controller="cloudauthz", conditions=dict(method=["GET"]))
    webapp.mapper.connect(
        "/api/cloud/authz/", action="create", controller="cloudauthz", conditions=dict(method=["POST"])
    )

    webapp.mapper.connect(
        "delete_cloudauthz_item",
        "/api/cloud/authz/{encoded_authz_id}",
        action="delete",
        controller="cloudauthz",
        conditions=dict(method=["DELETE"]),
    )

    webapp.mapper.connect(
        "upload_cloudauthz_item",
        "/api/cloud/authz/{encoded_authz_id}",
        action="update",
        controller="cloudauthz",
        conditions=dict(method=["PUT"]),
    )

    # =======================
    # ====== TOOLS API ======
    # =======================

    webapp.mapper.connect("/api/tools/all_requirements", action="all_requirements", controller="tools")
    webapp.mapper.connect("/api/tools/error_stack", action="error_stack", controller="tools")
    webapp.mapper.connect("/api/tools/{id:.+?}/build", action="build", controller="tools")
    webapp.mapper.connect("/api/tools/{id:.+?}/reload", action="reload", controller="tools")
    webapp.mapper.connect("/api/tools/tests_summary", action="tests_summary", controller="tools")
    webapp.mapper.connect("/api/tools/{id:.+?}/test_data_path", action="test_data_path", controller="tools")
    webapp.mapper.connect("/api/tools/{id:.+?}/test_data_download", action="test_data_download", controller="tools")
    webapp.mapper.connect("/api/tools/{id:.+?}/test_data", action="test_data", controller="tools")
    webapp.mapper.connect("/api/tools/{id:.+?}/diagnostics", action="diagnostics", controller="tools")
    webapp.mapper.connect("/api/tools/{id:.+?}/citations", action="citations", controller="tools")
    webapp.mapper.connect(
        "/api/tools/{tool_id:.+?}/convert", action="conversion", controller="tools", conditions=dict(method=["POST"])
    )
    webapp.mapper.connect("/api/tools/{id:.+?}/xrefs", action="xrefs", controller="tools")
    webapp.mapper.connect("/api/tools/{id:.+?}/download", action="download", controller="tools")
    webapp.mapper.connect("/api/tools/{id:.+?}/raw_tool_source", action="raw_tool_source", controller="tools")
    webapp.mapper.connect("/api/tools/{id:.+?}/requirements", action="requirements", controller="tools")
    webapp.mapper.connect(
        "/api/tools/{id:.+?}/install_dependencies",
        action="install_dependencies",
        controller="tools",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect(
        "/api/tools/{id:.+?}/dependencies",
        action="install_dependencies",
        controller="tools",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect(
        "/api/tools/{id:.+?}/dependencies",
        action="uninstall_dependencies",
        controller="tools",
        conditions=dict(method=["DELETE"]),
    )
    webapp.mapper.connect(
        "/api/tools/{id:.+?}/build_dependency_cache",
        action="build_dependency_cache",
        controller="tools",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect("/api/tools/{id:.+?}", action="show", controller="tools")
    webapp.mapper.resource("tool", "tools", path_prefix="/api")
    webapp.mapper.resource("dynamic_tools", "dynamic_tools", path_prefix="/api")

    webapp.mapper.connect(
        "/api/sanitize_allow", action="index", controller="sanitize_allow", conditions=dict(method=["GET"])
    )
    webapp.mapper.connect(
        "/api/sanitize_allow", action="create", controller="sanitize_allow", conditions=dict(method=["PUT"])
    )
    webapp.mapper.connect(
        "/api/sanitize_allow", action="delete", controller="sanitize_allow", conditions=dict(method=["DELETE"])
    )

    webapp.mapper.connect("/api/entry_points", action="index", controller="tool_entry_points")
    webapp.mapper.connect(
        "/api/entry_points/{id:.+?}/access", action="access_entry_point", controller="tool_entry_points"
    )
    webapp.mapper.connect(
        "/api/entry_points/{id:.+?}",
        action="stop_entry_point",
        controller="tool_entry_points",
        conditions={"method": ["DELETE"]},
    )

    webapp.mapper.connect(
        "/api/dependency_resolvers/clean",
        action="clean",
        controller="tool_dependencies",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect(
        "/api/dependency_resolvers/dependency",
        action="manager_dependency",
        controller="tool_dependencies",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "/api/dependency_resolvers/dependency",
        action="install_dependency",
        controller="tool_dependencies",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect(
        "/api/dependency_resolvers/requirements", action="manager_requirements", controller="tool_dependencies"
    )
    webapp.mapper.connect(
        "/api/dependency_resolvers/unused_paths",
        action="unused_dependency_paths",
        controller="tool_dependencies",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "/api/dependency_resolvers/unused_paths",
        action="delete_unused_dependency_paths",
        controller="tool_dependencies",
        conditions=dict(method=["PUT"]),
    )
    webapp.mapper.connect(
        "/api/dependency_resolvers/toolbox",
        controller="tool_dependencies",
        action="summarize_toolbox",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "/api/dependency_resolvers/toolbox/install",
        controller="tool_dependencies",
        action="toolbox_install",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect(
        "/api/dependency_resolvers/toolbox/uninstall",
        controller="tool_dependencies",
        action="toolbox_uninstall",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect(
        "/api/dependency_resolvers/{index}/clean",
        action="clean",
        controller="tool_dependencies",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect(
        "/api/dependency_resolvers/{index}/dependency",
        action="resolver_dependency",
        controller="tool_dependencies",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "/api/dependency_resolvers/{index}/dependency",
        action="install_dependency",
        controller="tool_dependencies",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect(
        "/api/dependency_resolvers/{index}/requirements", action="resolver_requirements", controller="tool_dependencies"
    )
    webapp.mapper.resource(
        "dependency_resolver", "dependency_resolvers", controller="tool_dependencies", path_prefix="api"
    )
    webapp.mapper.connect(
        "/api/container_resolvers", action="index", controller="container_resolution", conditions=dict(method=["GET"])
    )
    webapp.mapper.connect(
        "/api/container_resolvers/resolve",
        action="resolve",
        controller="container_resolution",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "/api/container_resolvers/toolbox",
        action="resolve_toolbox",
        controller="container_resolution",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "/api/container_resolvers/resolve/install",
        action="resolve_with_install",
        controller="container_resolution",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect(
        "/api/container_resolvers/toolbox/install",
        action="resolve_toolbox_with_install",
        controller="container_resolution",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect(
        "/api/container_resolvers/{index}",
        action="show",
        controller="container_resolution",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "/api/container_resolvers/{index}/resolve",
        action="resolve",
        controller="container_resolution",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "/api/container_resolvers/{index}/toolbox",
        action="resolve_toolbox",
        controller="container_resolution",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "/api/container_resolvers/{index}/resolve/install",
        action="resolve_with_install",
        controller="container_resolution",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect(
        "/api/container_resolvers/{index}/toolbox/install",
        action="resolve_toolbox_with_install",
        controller="container_resolution",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect(
        "/api/workflows/get_tool_predictions",
        action="get_tool_predictions",
        controller="workflows",
        conditions=dict(method=["POST"]),
    )

    webapp.mapper.resource_with_deleted("user", "users", path_prefix="/api")
    webapp.mapper.resource("visualization", "visualizations", path_prefix="/api")
    webapp.mapper.resource("plugins", "plugins", path_prefix="/api")
    webapp.mapper.connect("/api/workflows/build_module", action="build_module", controller="workflows")
    webapp.mapper.connect(
        "/api/workflows/menu", action="get_workflow_menu", controller="workflows", conditions=dict(method=["GET"])
    )
    webapp.mapper.connect(
        "/api/workflows/menu", action="set_workflow_menu", controller="workflows", conditions=dict(method=["PUT"])
    )
    webapp.mapper.connect(
        "/api/workflows/{id}/refactor", action="refactor", controller="workflows", conditions=dict(method=["PUT"])
    )
    webapp.mapper.resource("workflow", "workflows", path_prefix="/api")
    webapp.mapper.resource("search", "search", path_prefix="/api")

    # ---- visualizations registry ---- generic template renderer
    # @deprecated: this route should be considered deprecated
    webapp.add_route(
        "/visualization/show/{visualization_name}", controller="visualization", action="render", visualization_name=None
    )

    # provide an alternate route to visualization plugins that's closer to their static assets
    # (/plugins/visualizations/{visualization_name}/static) and allow them to use relative urls to those
    webapp.mapper.connect(
        "visualization_plugin",
        "/plugins/visualizations/{visualization_name}/show",
        controller="visualization",
        action="render",
    )
    webapp.mapper.connect(
        "saved_visualization",
        "/plugins/visualizations/{visualization_name}/saved",
        controller="visualization",
        action="saved",
    )
    # Deprecated in favor of POST /api/workflows with 'workflow' in payload.
    webapp.mapper.connect(
        "import_workflow_deprecated",
        "/api/workflows/upload",
        controller="workflows",
        action="import_new_workflow_deprecated",
        conditions=dict(method=["POST"]),
    )
    webapp.mapper.connect(
        "workflow_dict",
        "/api/workflows/{workflow_id}/download",
        controller="workflows",
        action="workflow_dict",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "show_versions",
        "/api/workflows/{workflow_id}/versions",
        controller="workflows",
        action="show_versions",
        conditions=dict(method=["GET"]),
    )
    # Preserve the following download route for now for dependent applications  -- deprecate at some point
    webapp.mapper.connect(
        "workflow_dict",
        "/api/workflows/download/{workflow_id}",
        controller="workflows",
        action="workflow_dict",
        conditions=dict(method=["GET"]),
    )
    # Deprecated in favor of POST /api/workflows with shared_workflow_id in payload.
    webapp.mapper.connect(
        "import_shared_workflow_deprecated",
        "/api/workflows/import",
        controller="workflows",
        action="import_shared_workflow_deprecated",
        conditions=dict(method=["POST"]),
    )

    webapp.mapper.connect(
        "trs_search", "/api/trs_search", controller="trs_search", action="index", conditions=dict(method=["GET"])
    )
    webapp.mapper.connect(
        "trs_consume_get_servers",
        "/api/trs_consume/servers",
        controller="trs_consumer",
        action="get_servers",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "trs_consume_get_tool",
        "/api/trs_consume/{trs_server}/tools/{tool_id}",
        controller="trs_consumer",
        action="get_tool",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "trs_consume_get_tool_versions",
        "/api/trs_consume/{trs_server}/tools/{tool_id}/versions",
        controller="trs_consumer",
        action="get_versions",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "trs_consume_get_tool_version",
        "/api/trs_consume/{trs_server}/tools/{tool_id}/versions/{version_id}",
        controller="trs_consumer",
        action="get_version",
        conditions=dict(method=["GET"]),
    )
    # Not sure what this is supposed to refer to, import_tool_version does not exist
    # webapp.mapper.connect(
    #     "trs_consume_import_tool_version",
    #     "/api/trs_consume/{trs_server}/tools/{tool_id}/versions/{version_id}/import",
    #     controller="trs_consumer",
    #     action="import_tool_version",
    #     conditions=dict(method=["POST"]),
    # )

    webapp.mapper.connect(
        "list_invocations",
        "/api/invocations",
        controller="workflows",
        action="index_invocations",
        conditions=dict(method=["GET"]),
    )

    # API refers to usages and invocations - these mean the same thing but the
    # usage routes should be considered deprecated.
    invoke_names = {
        "invocations": "",
        "usage": "_deprecated",
    }
    for noun, suffix in invoke_names.items():
        name = f"{noun}{suffix}"
        webapp.mapper.connect(
            f"list_workflow_{name}",
            "/api/workflows/{workflow_id}/%s" % noun,
            controller="workflows",
            action="index_invocations",
            conditions=dict(method=["GET"]),
        )
        webapp.mapper.connect(
            f"workflow_{name}",
            "/api/workflows/{workflow_id}/%s" % noun,
            controller="workflows",
            action="invoke",
            conditions=dict(method=["POST"]),
        )

    def connect_invocation_endpoint(endpoint_name, endpoint_suffix, action, conditions=None):
        # /api/invocations/<invocation_id>
        # /api/workflows/<workflow_id>/invocations/<invocation_id>
        # /api/workflows/<workflow_id>/usage/<invocation_id> (deprecated)
        conditions = conditions or dict(method=["GET"])
        webapp.mapper.connect(
            f"workflow_invocation_{endpoint_name}",
            f"/api/workflows/{{workflow_id}}/invocations/{{invocation_id}}{endpoint_suffix}",
            controller="workflows",
            action=action,
            conditions=conditions,
        )
        webapp.mapper.connect(
            f"workflow_usage_{endpoint_name}",
            f"/api/workflows/{{workflow_id}}/usage/{{invocation_id}}{endpoint_suffix}",
            controller="workflows",
            action=action,
            conditions=conditions,
        )
        webapp.mapper.connect(
            f"invocation_{endpoint_name}",
            f"/api/invocations/{{invocation_id}}{endpoint_suffix}",
            controller="workflows",
            action=action,
            conditions=conditions,
        )

    connect_invocation_endpoint("show", "", action="show_invocation")
    connect_invocation_endpoint("show_report", "/report", action="show_invocation_report")
    connect_invocation_endpoint("show_report_pdf", "/report.pdf", action="show_invocation_report_pdf")
    connect_invocation_endpoint("biocompute/download", "/biocompute/download", action="download_invocation_bco")
    connect_invocation_endpoint("biocompute", "/biocompute", action="export_invocation_bco")
    connect_invocation_endpoint("jobs_summary", "/jobs_summary", action="invocation_jobs_summary")
    connect_invocation_endpoint("step_jobs_summary", "/step_jobs_summary", action="invocation_step_jobs_summary")
    connect_invocation_endpoint("cancel", "", action="cancel_invocation", conditions=dict(method=["DELETE"]))
    connect_invocation_endpoint("show_step", "/steps/{step_id}", action="invocation_step")
    connect_invocation_endpoint(
        "update_step", "/steps/{step_id}", action="update_invocation_step", conditions=dict(method=["PUT"])
    )

    # ============================
    # ===== AUTHENTICATE API =====
    # ============================

    webapp.mapper.connect(
        "api_key_retrieval",
        "/api/authenticate/baseauth/",
        controller="authenticate",
        action="get_api_key",
        conditions=dict(method=["GET"]),
    )

    # ======================================
    # ====== DISPLAY APPLICATIONS API ======
    # ======================================

    webapp.mapper.connect(
        "index",
        "/api/display_applications",
        controller="display_applications",
        action="index",
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.connect(
        "reload",
        "/api/display_applications/reload",
        controller="display_applications",
        action="reload",
        conditions=dict(method=["POST"]),
    )

    # ================================
    # ===== USERS API =====
    # ================================

    webapp.mapper.connect(
        "api_key", "/api/users/{id}/api_key", controller="users", action="api_key", conditions=dict(method=["POST"])
    )

    webapp.mapper.connect(
        "api_key",
        "/api/users/{id}/api_key",
        controller="users",
        action="get_or_create_api_key",
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.connect(
        "get_api_key",
        "/api/users/{id}/api_key/inputs",
        controller="users",
        action="get_api_key",
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.connect(
        "set_api_key",
        "/api/users/{id}/api_key/inputs",
        controller="users",
        action="set_api_key",
        conditions=dict(method=["PUT"]),
    )

    webapp.mapper.connect(
        "get_information",
        "/api/users/{id}/information/inputs",
        controller="users",
        action="get_information",
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.connect(
        "set_information",
        "/api/users/{id}/information/inputs",
        controller="users",
        action="set_information",
        conditions=dict(method=["PUT"]),
    )

    webapp.mapper.connect(
        "get_password",
        "/api/users/{id}/password/inputs",
        controller="users",
        action="get_password",
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.connect(
        "set_password",
        "/api/users/{id}/password/inputs",
        controller="users",
        action="set_password",
        conditions=dict(method=["PUT"]),
    )

    webapp.mapper.connect(
        "get_permissions",
        "/api/users/{id}/permissions/inputs",
        controller="users",
        action="get_permissions",
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.connect(
        "set_permissions",
        "/api/users/{id}/permissions/inputs",
        controller="users",
        action="set_permissions",
        conditions=dict(method=["PUT"]),
    )

    webapp.mapper.connect(
        "get_toolbox_filters",
        "/api/users/{id}/toolbox_filters/inputs",
        controller="users",
        action="get_toolbox_filters",
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.connect(
        "set_toolbox_filters",
        "/api/users/{id}/toolbox_filters/inputs",
        controller="users",
        action="set_toolbox_filters",
        conditions=dict(method=["PUT"]),
    )

    webapp.mapper.connect(
        "get_custom_builds",
        "/api/users/{id}/custom_builds",
        controller="users",
        action="get_custom_builds",
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.connect(
        "add_custom_builds",
        "/api/users/{id}/custom_builds/{key}",
        controller="users",
        action="add_custom_builds",
        conditions=dict(method=["PUT"]),
    )

    webapp.mapper.connect(
        "delete_custom_builds",
        "/api/users/{id}/custom_builds/{key}",
        controller="users",
        action="delete_custom_builds",
        conditions=dict(method=["DELETE"]),
    )

    webapp.mapper.connect(
        "set_favorite_tool",
        "/api/users/{id}/favorites/{object_type}",
        controller="users",
        action="set_favorite",
        conditions=dict(method=["PUT"]),
    )

    webapp.mapper.connect(
        "remove_favorite_tool",
        "/api/users/{id}/favorites/{object_type}/{object_id:.*?}",
        controller="users",
        action="remove_favorite",
        conditions=dict(method=["DELETE"]),
    )

    # ========================
    # ===== WEBHOOKS API =====
    # ========================

    webapp.mapper.connect(
        "get_all_webhooks",
        "/api/webhooks",
        controller="webhooks",
        action="all_webhooks",
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.connect(
        "get_webhook_data",
        "/api/webhooks/{webhook_id}/data",
        controller="webhooks",
        action="webhook_data",
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.connect(
        "show_ld_item",
        "/api/libraries/datasets/{id}",
        controller="library_datasets",
        action="show",
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.connect(
        "load_ld",
        "/api/libraries/datasets/",
        controller="library_datasets",
        action="load",
        conditions=dict(method=["POST"]),
    )

    webapp.mapper.connect(
        "show_version_of_ld_item",
        "/api/libraries/datasets/{encoded_dataset_id}/versions/{encoded_ldda_id}",
        controller="library_datasets",
        action="show_version",
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.connect(
        "update_ld",
        "/api/libraries/datasets/{encoded_dataset_id}",
        controller="library_datasets",
        action="update",
        conditions=dict(method=["PATCH"]),
    )

    webapp.mapper.connect(
        "show_legitimate_ld_roles",
        "/api/libraries/datasets/{encoded_dataset_id}/permissions",
        controller="library_datasets",
        action="show_roles",
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.connect(
        "update_ld_permissions",
        "/api/libraries/datasets/{encoded_dataset_id}/permissions",
        controller="library_datasets",
        action="update_permissions",
        conditions=dict(method=["POST"]),
    )

    webapp.mapper.connect(
        "delete_ld_item",
        "/api/libraries/datasets/{encoded_dataset_id}",
        controller="library_datasets",
        action="delete",
        conditions=dict(method=["DELETE"]),
    )

    webapp.mapper.connect(
        "download_ld_items",
        "/api/libraries/datasets/download/{archive_format}",
        controller="library_datasets",
        action="download",
        conditions=dict(method=["POST", "GET"]),
    )

    webapp.mapper.resource(
        "content",
        "contents",
        controller="library_contents",
        name_prefix="library_",
        path_prefix="/api/libraries/{library_id}",
        parent_resources=dict(member_name="library", collection_name="libraries"),
    )

    _add_item_extended_metadata_controller(
        webapp, name_prefix="library_dataset_", path_prefix="/api/libraries/{library_id}/contents/{library_content_id}"
    )

    # =======================
    # ===== FOLDERS API =====
    # =======================

    webapp.mapper.connect(
        "add_history_datasets_to_library",
        "/api/folders/{encoded_folder_id}/contents",
        controller="folder_contents",
        action="create",
        conditions=dict(method=["POST"]),
    )

    webapp.mapper.resource(
        "content",
        "contents",
        controller="folder_contents",
        name_prefix="folder_",
        path_prefix="/api/folders/{folder_id}",
        parent_resources=dict(member_name="folder", collection_name="folders"),
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.resource("job", "jobs", path_prefix="/api")
    webapp.mapper.connect(
        "job_search", "/api/jobs/search", controller="jobs", action="search", conditions=dict(method=["POST"])
    )
    webapp.mapper.connect(
        "job_inputs", "/api/jobs/{id}/inputs", controller="jobs", action="inputs", conditions=dict(method=["GET"])
    )
    webapp.mapper.connect(
        "job_outputs", "/api/jobs/{id}/outputs", controller="jobs", action="outputs", conditions=dict(method=["GET"])
    )
    webapp.mapper.connect(
        "build_for_rerun",
        "/api/jobs/{id}/build_for_rerun",
        controller="jobs",
        action="build_for_rerun",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "resume", "/api/jobs/{id}/resume", controller="jobs", action="resume", conditions=dict(method=["PUT"])
    )
    webapp.mapper.connect(
        "job_error", "/api/jobs/{id}/error", controller="jobs", action="error", conditions=dict(method=["POST"])
    )
    webapp.mapper.connect(
        "common_problems",
        "/api/jobs/{id}/common_problems",
        controller="jobs",
        action="common_problems",
        conditions=dict(method=["GET"]),
    )
    # Job metrics and parameters by job id or dataset id (for slightly different accessibility checking)
    webapp.mapper.connect(
        "destination_params",
        "/api/jobs/{job_id}/destination_params",
        controller="jobs",
        action="destination_params",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "dataset_metrics",
        "/api/datasets/{dataset_id}/metrics",
        controller="jobs",
        action="metrics",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "parameters_display",
        "/api/jobs/{job_id}/parameters_display",
        controller="jobs",
        action="parameters_display",
        conditions=dict(method=["GET"]),
    )
    webapp.mapper.connect(
        "dataset_parameters_display",
        "/api/datasets/{dataset_id}/parameters_display",
        controller="jobs",
        action="parameters_display",
        conditions=dict(method=["GET"]),
    )

    # Job files controllers. Only for consumption by remote job runners.
    webapp.mapper.resource(
        "file",
        "files",
        controller="job_files",
        name_prefix="job_",
        path_prefix="/api/jobs/{job_id}",
        parent_resources=dict(member_name="job", collection_name="jobs"),
    )
    webapp.mapper.resource(
        "port",
        "ports",
        controller="job_ports",
        name_prefix="job_",
        path_prefix="/api/jobs/{job_id}",
        parent_resources=dict(member_name="job", collection_name="jobs"),
    )

    _add_item_extended_metadata_controller(
        webapp, name_prefix="history_dataset_", path_prefix="/api/histories/{history_id}/contents/{history_content_id}"
    )

    # ====================
    # ===== TOOLSHED =====
    # ====================

    # Handle displaying tool help images and README file images contained in repositories installed from the tool shed.
    webapp.add_route(
        "/admin_toolshed/static/images/{repository_id}/{image_file:.+?}",
        controller="admin_toolshed",
        action="display_image_in_repository",
        repository_id=None,
        image_file=None,
    )

    # Do the same but without a repository id
    webapp.add_route(
        "/shed_tool_static/{shed}/{owner}/{repo}/{tool}/{version}/{image_file:.+?}",
        controller="shed_tool_static",
        action="index",
        shed=None,
        owner=None,
        repo=None,
        tool=None,
        version=None,
        image_file=None,
    )

    webapp.mapper.connect(
        "tool_shed_contents",
        "/api/tool_shed/contents",
        controller="toolshed",
        action="show",
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.connect(
        "tool_sheds", "/api/tool_shed", controller="toolshed", action="index", conditions=dict(method=["GET"])
    )

    webapp.mapper.connect(
        "tool_shed_request",
        "/api/tool_shed/request",
        controller="toolshed",
        action="request",
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.connect(
        "install_repository",
        "/api/tool_shed_repositories",
        controller="tool_shed_repositories",
        action="install_repository_revision",
        conditions=dict(method=["POST"]),
    )

    webapp.mapper.connect(
        "check_for_updates",
        "/api/tool_shed_repositories/check_for_updates",
        controller="tool_shed_repositories",
        action="check_for_updates",
        conditions=dict(method=["GET"]),
    )

    webapp.mapper.connect(
        "tool_shed_repository",
        "/api/tool_shed_repositories",
        controller="tool_shed_repositories",
        action="uninstall_repository",
        conditions=dict(method=["DELETE"]),
    )

    webapp.mapper.connect(
        "tool_shed_repository",
        "/api/tool_shed_repositories/{id}",
        controller="tool_shed_repositories",
        action="uninstall_repository",
        conditions=dict(method=["DELETE"]),
    )

    webapp.mapper.connect(
        "reset_metadata_on_selected_installed_repositories",
        "/api/tool_shed_repositories/reset_metadata_on_selected_installed_repositories",
        controller="tool_shed_repositories",
        action="reset_metadata_on_selected_installed_repositories",
        conditions=dict(method=["POST"]),
    )

    # Galaxy API for tool shed features.
    webapp.mapper.resource(
        "tool_shed_repository",
        "tool_shed_repositories",
        collection={"reset_metadata_on_installed_repositories": "POST"},
        controller="tool_shed_repositories",
        name_prefix="tool_shed_repository_",
        path_prefix="/api",
        new={"install_repository_revision": "POST"},
        parent_resources=dict(member_name="tool_shed_repository", collection_name="tool_shed_repositories"),
    )

    # ==== Trace/Metrics Logger
    # Connect logger from app
    if app.trace_logger:
        webapp.trace_logger = app.trace_logger


def _add_item_tags_controller(webapp, name_prefix, path_prefix, **kwd):
    # Not just using map.resources because actions should be based on name not id
    controller = f"{name_prefix}tags"
    name = f"{name_prefix}tag"
    path = f"{path_prefix}/tags"
    map = webapp.mapper
    # Allow view items' tags.
    map.connect(name, path, controller=controller, action="index", conditions=dict(method=["GET"]))
    # Allow remove tag from item
    map.connect(
        f"{name}_delete",
        "%s/tags/{tag_name}" % path_prefix,
        controller=controller,
        action="delete",
        conditions=dict(method=["DELETE"]),
    )
    # Allow create a new tag with from name
    map.connect(
        f"{name}_create",
        "%s/tags/{tag_name}" % path_prefix,
        controller=controller,
        action="create",
        conditions=dict(method=["POST"]),
    )
    # Allow update tag value
    map.connect(
        f"{name}_update",
        "%s/tags/{tag_name}" % path_prefix,
        controller=controller,
        action="update",
        conditions=dict(method=["PUT"]),
    )
    # Allow show tag by name
    map.connect(
        f"{name}_show",
        "%s/tags/{tag_name}" % path_prefix,
        controller=controller,
        action="show",
        conditions=dict(method=["GET"]),
    )


def _add_item_extended_metadata_controller(webapp, name_prefix, path_prefix, **kwd):
    controller = f"{name_prefix}extended_metadata"
    name = f"{name_prefix}extended_metadata"
    webapp.mapper.resource(name, "extended_metadata", path_prefix=path_prefix, controller=controller)


def _add_item_annotation_controller(webapp, name_prefix, path_prefix, **kwd):
    controller = f"{name_prefix}annotations"
    name = f"{name_prefix}annotation"
    webapp.mapper.resource(name, "annotation", path_prefix=path_prefix, controller=controller)


def _add_item_provenance_controller(webapp, name_prefix, path_prefix, **kwd):
    controller = f"{name_prefix}provenance"
    name = f"{name_prefix}provenance"
    webapp.mapper.resource(name, "provenance", path_prefix=path_prefix, controller=controller)


def wrap_in_middleware(app, global_conf, application_stack, **local_conf):
    """
    Based on the configuration wrap `app` in a set of common and useful
    middleware.
    """
    webapp = app
    stack = application_stack

    # Merge the global and local configurations
    conf = global_conf.copy()
    conf.update(local_conf)
    debug = asbool(conf.get("debug", False))
    # First put into place httpexceptions, which must be most closely
    # wrapped around the application (it can interact poorly with
    # other middleware):
    app = wrap_if_allowed(app, stack, httpexceptions.make_middleware, name="paste.httpexceptions", args=(conf,))
    # Statsd request timing and profiling
    statsd_host = conf.get("statsd_host", None)
    if statsd_host:
        from galaxy.web.framework.middleware.statsd import StatsdMiddleware

        app = wrap_if_allowed(
            app,
            stack,
            StatsdMiddleware,
            args=(
                statsd_host,
                conf.get("statsd_port", 8125),
                conf.get("statsd_prefix", "galaxy"),
                conf.get("statsd_influxdb", False),
                conf.get("statsd_mock_calls", False),
            ),
        )
        log.info("Enabling 'statsd' middleware")
    # If we're using remote_user authentication, add middleware that
    # protects Galaxy from improperly configured authentication in the
    # upstream server
    single_user = conf.get("single_user", None)
    use_remote_user = asbool(conf.get("use_remote_user", False)) or single_user
    if use_remote_user:
        from galaxy.web.framework.middleware.remoteuser import RemoteUser

        app = wrap_if_allowed(
            app,
            stack,
            RemoteUser,
            kwargs=dict(
                maildomain=conf.get("remote_user_maildomain", None),
                display_servers=util.listify(conf.get("display_servers", "")),
                single_user=single_user,
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
    # If sentry logging is enabled, log here before propogating up to
    # the error middleware
    sentry_dsn = conf.get("sentry_dsn", None)
    if sentry_dsn:
        from sentry_sdk.integrations.wsgi import SentryWsgiMiddleware

        app = wrap_if_allowed(app, stack, SentryWsgiMiddleware)
    # Various debug middleware that can only be turned on if the debug
    # flag is set, either because they are insecure or greatly hurt
    # performance
    if debug:
        # Middleware to check for WSGI compliance
        if asbool(conf.get("use_lint", False)):
            from paste import lint

            app = wrap_if_allowed(app, stack, lint.make_middleware, name="paste.lint", args=(conf,))
        # Middleware to run the python profiler on each request
        if asbool(conf.get("use_profile", False)):
            from paste.debug import profile

            app = wrap_if_allowed(app, stack, profile.ProfileMiddleware, args=(conf,))
    # Error middleware
    app = wrap_if_allowed(app, stack, ErrorMiddleware, args=(conf,))
    # Transaction logging (apache access.log style)
    if asbool(conf.get("use_translogger", True)):
        from galaxy.web.framework.middleware.translogger import TransLogger

        app = wrap_if_allowed(app, stack, TransLogger)
    # TUS upload middleware
    app = wrap_if_allowed(
        app,
        stack,
        TusMiddleware,
        kwargs={
            "upload_path": urljoin(f"{application_stack.config.galaxy_url_prefix}/", "api/upload/resumable_upload"),
            "tmp_dir": application_stack.config.tus_upload_store or application_stack.config.new_file_path,
            "max_size": application_stack.config.maximum_upload_file_size,
        },
    )
    # X-Forwarded-Host handling
    app = wrap_if_allowed(app, stack, XForwardedHostMiddleware)
    # Request ID middleware
    app = wrap_if_allowed(app, stack, RequestIDMiddleware)
    if asbool(conf.get("enable_per_request_sql_debugging", False)):
        from galaxy.web.framework.middleware.sqldebug import SQLDebugMiddleware

        app = wrap_if_allowed(app, stack, SQLDebugMiddleware, args=(webapp, {}))
    return app
