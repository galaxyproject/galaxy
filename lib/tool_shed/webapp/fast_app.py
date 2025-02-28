import logging
import os
from pathlib import Path
from typing import (
    Any,
    cast,
    Dict,
    Optional,
)

from a2wsgi import WSGIMiddleware
from fastapi import (
    Depends,
    FastAPI,
)
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette_graphene3 import (
    GraphQLApp,
    make_graphiql_handler,
)

from galaxy.webapps.base.api import (
    add_exception_handler,
    add_request_id_middleware,
    include_all_package_routers,
)
from galaxy.webapps.openapi.utils import get_openapi
from tool_shed.structured_app import ToolShedApp
from tool_shed.webapp.api2 import (
    ensure_valid_session,
    get_trans,
)
from tool_shed.webapp.graphql.schema import schema

log = logging.getLogger(__name__)

api_tags_metadata = [
    {
        "name": "authenticate",
        "description": "Authentication-related endpoints.",
    },
    {
        "name": "categories",
        "description": "Category-related endpoints.",
    },
    {
        "name": "repositories",
        "description": "Repository-related endpoints.",
    },
    {
        "name": "users",
        "description": "User-related endpoints.",
    },
    {"name": "undocumented", "description": "API routes that have not yet been ported to FastAPI."},
]

# Set this if asset handling should be sent to vite.
# Run vite with:
#   yarn dev
# Start tool shed with:
#   TOOL_SHED_VITE_PORT=4040 TOOL_SHED_API_VERSION=v2 ./run_tool_shed.sh
TOOL_SHED_VITE_PORT: Optional[str] = os.environ.get("TOOL_SHED_VITE_PORT", None)
TOOL_SHED_FRONTEND_TARGET: str = os.environ.get("TOOL_SHED_FRONTEND_TARGET") or "auto"  # auto, src, or node
TOOL_SHED_USE_HMR: bool = TOOL_SHED_VITE_PORT is not None
WEBAPP_DIR = Path(__file__).parent.resolve()
FRONTEND = WEBAPP_DIR / "frontend"
FRONTEND_DIST = FRONTEND / "dist"
INSTALLED_FRONTEND = WEBAPP_DIR / "node_modules" / "@galaxyproject" / "tool-shed-frontend" / "dist"
INDEX_FILENAME = "index.html"


def find_frontend_target() -> Path:
    src_target = FRONTEND_DIST
    node_target = INSTALLED_FRONTEND
    if TOOL_SHED_FRONTEND_TARGET == "src":
        return src_target
    elif TOOL_SHED_FRONTEND_TARGET == "node":
        return node_target
    elif src_target.exists():
        return src_target
    else:
        return node_target


def frontend_controller(app):
    shed_entry_point = "main.ts"
    vite_runtime = "@vite/client"

    def index(trans=Depends(get_trans)):
        if TOOL_SHED_USE_HMR:
            if TOOL_SHED_FRONTEND_TARGET != "auto":
                raise Exception("Cannot configure HMR and with this frontend target.")
            index = FRONTEND / INDEX_FILENAME
            index_html = index.read_text()
            index_html = index_html.replace(
                f"""<script type="module" src="/src/{shed_entry_point}"></script>""",
                f"""<script type="module" src="http://localhost:{TOOL_SHED_VITE_PORT}/{vite_runtime}"></script><script type="module" src="http://localhost:{TOOL_SHED_VITE_PORT}/src/{shed_entry_point}"></script>""",
            )
        else:
            index = find_frontend_target() / INDEX_FILENAME
            index_html = index.read_text()
        ensure_valid_session(trans)
        cookie = trans.session_csrf_token
        r: HTMLResponse = cast(HTMLResponse, trans.response)
        r.set_cookie("session_csrf_token", cookie)
        return index_html

    return app, index


def redirect_route(app, from_url: str, to_url: str):
    @app.get(from_url)
    def redirect():
        return RedirectResponse(to_url)


def frontend_route(controller, path):
    app, index = controller
    app.get(path, response_class=HTMLResponse)(index)


def mount_graphql(app: FastAPI, tool_shed_app: ToolShedApp):
    context = {
        "session": tool_shed_app.model.context,
        "security": tool_shed_app.security,
    }
    g_app = GraphQLApp(schema, on_get=make_graphiql_handler(), context_value=context, root_value=context)
    app.mount("/graphql", g_app)
    app.mount("/api/graphql", g_app)


FRONT_END_ROUTES = [
    "/",
    "/admin",
    "/login",
    "/register",
    "/logout_success",
    "/login_success",
    "/registration_success",
    "/help",
    "/repositories_by_search",
    "/repositories_by_category",
    "/repositories_by_category/{category_id}",
    "/repositories_by_owner",
    "/repositories_by_owner/{username}",
    "/repositories/{repository_id}",
    "/repositories_search",
    "/_component_showcase",
    "/user/api_key",
    "/user/change_password",
    "/user/change_password_success",
    "/view/{username}",
    "/view/{username}/{repository_name}",
    "/view/{username}/{repository_name}/{changeset_revision}",
]
LEGACY_ROUTES = {
    "/user/create": "/register",  # for twilltestcase
    "/user/login": "/login",  # for twilltestcase
}


limiter = Limiter(key_func=get_remote_address)


def initialize_fast_app(gx_webapp, tool_shed_app):
    app = get_fastapi_instance()
    add_exception_handler(app)
    add_request_id_middleware(app)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    from .config import SHED_API_VERSION

    def mount_static(directory: Path):
        name = directory.name
        if directory.exists():
            app.mount(f"/{name}", StaticFiles(directory=directory), name=name)

    if SHED_API_VERSION == "v2":
        controller = frontend_controller(app)
        for route in FRONT_END_ROUTES:
            frontend_route(controller, route)

        for from_route, to_route in LEGACY_ROUTES.items():
            redirect_route(app, from_route, to_route)

        mount_graphql(app, tool_shed_app)

        mount_static(FRONTEND / "static")
        if TOOL_SHED_USE_HMR:
            mount_static(FRONTEND / "node_modules")
        else:
            mount_static(find_frontend_target() / "assets")

    routes_package = "tool_shed.webapp.api" if SHED_API_VERSION == "v1" else "tool_shed.webapp.api2"
    include_all_package_routers(app, routes_package)
    wsgi_handler = WSGIMiddleware(gx_webapp)
    tool_shed_app.haltables.append(("WSGI Middleware threadpool", wsgi_handler.executor.shutdown))
    # https://github.com/abersheeran/a2wsgi/issues/44
    app.mount("/", wsgi_handler)  # type: ignore[arg-type]
    return app


def get_fastapi_instance() -> FastAPI:
    return FastAPI(
        title="Galaxy Tool Shed API",
        description=("This API allows you to manage the Tool Shed repositories."),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        tags=api_tags_metadata,
        license_info={"name": "MIT", "url": "https://github.com/galaxyproject/galaxy/blob/dev/LICENSE.txt"},
    )


def get_openapi_schema() -> Dict[str, Any]:
    """
    Dumps openAPI schema without starting a full app and webserver.
    """
    app = get_fastapi_instance()
    include_all_package_routers(app, "tool_shed.webapp.api2")
    return get_openapi(
        title=app.title,
        version=app.version,
        openapi_version="3.1.0",
        description=app.description,
        routes=app.routes,
        license_info=app.license_info,
    )


__all__ = (
    "add_request_id_middleware",
    "get_openapi_schema",
    "initialize_fast_app",
)
