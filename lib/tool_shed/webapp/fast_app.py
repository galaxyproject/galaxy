from typing import (
    Any,
    Dict,
)

from a2wsgi import WSGIMiddleware
from fastapi import FastAPI

from galaxy.webapps.base.api import (
    add_exception_handler,
    add_request_id_middleware,
    include_all_package_routers,
)
from galaxy.webapps.openapi.utils import get_openapi

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


def initialize_fast_app(gx_webapp, tool_shed_app):
    app = get_fastapi_instance()
    add_exception_handler(app)
    add_request_id_middleware(app)
    from .buildapp import SHED_API_VERSION

    routes_package = "tool_shed.webapp.api" if SHED_API_VERSION == "v1" else "tool_shed.webapp.api2"
    include_all_package_routers(app, routes_package)
    wsgi_handler = WSGIMiddleware(gx_webapp)
    tool_shed_app.haltables.append(("WSGI Middleware threadpool", wsgi_handler.executor.shutdown))
    app.mount("/", wsgi_handler)
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
