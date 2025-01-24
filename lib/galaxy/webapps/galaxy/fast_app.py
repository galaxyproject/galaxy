from typing import (
    Any,
    Dict,
)

from a2wsgi import WSGIMiddleware
from fastapi import (
    FastAPI,
    Request,
)
from fastapi.openapi.constants import REF_TEMPLATE
from starlette.middleware.cors import CORSMiddleware

from galaxy.schema.generics import CustomJsonSchema
from galaxy.version import VERSION
from galaxy.webapps.base.api import (
    add_exception_handler,
    add_raw_context_middlewares,
    add_request_id_middleware,
    GalaxyFileResponse,
    include_all_package_routers,
)
from galaxy.webapps.base.webapp import config_allows_origin
from galaxy.webapps.openapi.utils import get_openapi

# https://fastapi.tiangolo.com/tutorial/metadata/#metadata-for-tags
api_tags_metadata = [
    {
        "name": "configuration",
        "description": "Configuration-related endpoints.",
    },
    {"name": "datasets", "description": "Operations on datasets."},
    {"name": "dataset collections"},
    {
        "name": "datatypes",
        "description": "Operations with supported data types.",
    },
    {
        "name": "datatypes",
        "description": "Operations on dataset collections.",
    },
    {
        "name": "genomes",
        "description": "Operations with genome data.",
    },
    {
        "name": "group_roles",
        "description": "Operations with group roles.",
    },
    {
        "name": "groups",
        "description": "Operations with groups.",
    },
    {
        "name": "group_users",
        "description": "Operations with group users.",
    },
    {"name": "histories"},
    {"name": "libraries"},
    {"name": "data libraries folders"},
    {"name": "job_lock"},
    {"name": "metrics"},
    {"name": "default"},
    {"name": "users"},
    {"name": "jobs"},
    {"name": "roles"},
    {"name": "quotas"},
    {"name": "visualizations"},
    {"name": "pages"},
    {
        "name": "licenses",
        "description": "Operations with [SPDX licenses](https://spdx.org/licenses/).",
    },
    {
        "name": "tags",
        "description": "Operations with tags.",
    },
    {
        "name": "tool data tables",
        "description": "Operations with tool [Data Tables](https://galaxyproject.org/admin/tools/data-tables/).",
    },
    {
        "name": "tours",
        "description": "Operations with interactive tours.",
    },
    {
        "name": "remote files",
        "description": "Operations with remote dataset sources.",
    },
    {"name": "undocumented", "description": "API routes that have not yet been ported to FastAPI."},
]


class GalaxyCORSMiddleware(CORSMiddleware):
    def __init__(self, *args, **kwds):
        self.config = kwds.pop("config")
        super().__init__(*args, **kwds)

    def is_allowed_origin(self, origin: str) -> bool:
        return config_allows_origin(origin, self.config)


def add_galaxy_middleware(app: FastAPI, gx_app):
    if x_frame_options := gx_app.config.x_frame_options:

        @app.middleware("http")
        async def add_x_frame_options(request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Frame-Options"] = x_frame_options
            return response

    GalaxyFileResponse.nginx_x_accel_redirect_base = gx_app.config.nginx_x_accel_redirect_base
    GalaxyFileResponse.apache_xsendfile = gx_app.config.apache_xsendfile

    if gx_app.config.get("allowed_origin_hostnames", None):
        app.add_middleware(
            GalaxyCORSMiddleware,
            config=gx_app.config,
            allow_headers=["*"],
            allow_methods=["*"],
            max_age=600,
        )


def include_legacy_openapi(app, gx_app):
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Galaxy API",
        version=VERSION,
        routes=app.routes,
        tags=api_tags_metadata,
    )
    legacy_openapi = gx_app.api_spec.to_dict()
    legacy_openapi["paths"].update(openapi_schema["paths"])
    openapi_schema["paths"] = legacy_openapi["paths"]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def get_fastapi_instance(root_path="") -> FastAPI:
    return FastAPI(
        title="Galaxy API",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_tags=api_tags_metadata,
        license_info={"name": "MIT", "url": "https://github.com/galaxyproject/galaxy/blob/dev/LICENSE.txt"},
        root_path=root_path,
    )


def get_openapi_schema() -> Dict[str, Any]:
    """
    Dumps openAPI schema without starting a full app and webserver.
    """
    app = get_fastapi_instance()
    include_all_package_routers(app, "galaxy.webapps.galaxy.api")
    return get_openapi(
        title=app.title,
        version=app.version,
        openapi_version="3.1.0",
        description=app.description,
        routes=app.routes,
        license_info=app.license_info,
        schema_generator=CustomJsonSchema(ref_template=REF_TEMPLATE),
    )


def initialize_fast_app(gx_wsgi_webapp, gx_app):
    root_path = "" if gx_app.config.galaxy_url_prefix == "/" else gx_app.config.galaxy_url_prefix
    app = get_fastapi_instance(root_path=root_path)
    add_exception_handler(app)
    add_galaxy_middleware(app, gx_app)
    if gx_app.config.use_access_logging_middleware:
        add_raw_context_middlewares(app)
    else:
        add_request_id_middleware(app)
    include_all_package_routers(app, "galaxy.webapps.galaxy.api")
    include_legacy_openapi(app, gx_app)
    wsgi_handler = WSGIMiddleware(gx_wsgi_webapp)
    gx_app.haltables.append(("WSGI Middleware threadpool", wsgi_handler.executor.shutdown))
    app.mount("/", wsgi_handler)  # type: ignore[arg-type]
    if gx_app.config.galaxy_url_prefix != "/":
        parent_app = FastAPI()
        parent_app.mount(gx_app.config.galaxy_url_prefix, app=app)
        return parent_app
    return app


__all__ = (
    "add_galaxy_middleware",
    "initialize_fast_app",
)
