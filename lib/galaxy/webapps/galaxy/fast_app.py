import typing
from pathlib import Path
from typing import cast

from fastapi import FastAPI, Request
from fastapi.middleware.wsgi import WSGIMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import (
    FileResponse,
    Response,
)

from galaxy.webapps.base.api import (
    add_exception_handler,
    add_request_id_middleware,
    include_all_package_routers,
)
from galaxy.webapps.base.webapp import config_allows_origin


# https://fastapi.tiangolo.com/tutorial/metadata/#metadata-for-tags
api_tags_metadata = [
    {
        "name": "configuration",
        "description": "Configuration-related endpoints.",
    },
    {
        "name": "datatypes",
        "description": "Operations with supported data types.",
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
]


class GalaxyCORSMiddleware(CORSMiddleware):

    def __init__(self, *args, **kwds):
        self.config = kwds.pop("config")
        super().__init__(*args, **kwds)

    def is_allowed_origin(self, origin: str) -> bool:
        return config_allows_origin(origin, self.config)


def add_galaxy_middleware(app: FastAPI, gx_app):
    x_frame_options = gx_app.config.x_frame_options
    if x_frame_options:

        @app.middleware("http")
        async def add_x_frame_options(request: Request, call_next):
            response = await call_next(request)
            response.headers['X-Frame-Options'] = x_frame_options
            return response

    nginx_x_accel_redirect_base = gx_app.config.nginx_x_accel_redirect_base
    apache_xsendfile = gx_app.config.apache_xsendfile

    if gx_app.config.sentry_dsn:
        from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
        app.add_middleware(SentryAsgiMiddleware)

    if nginx_x_accel_redirect_base or apache_xsendfile:

        @app.middleware("http")
        async def add_send_file_header(request: Request, call_next) -> Response:
            response = await call_next(request)
            if not isinstance(response, FileResponse):
                return response
            response = cast(FileResponse, response)
            if nginx_x_accel_redirect_base:
                full_path = Path(nginx_x_accel_redirect_base) / response.path
                response.headers['X-Accel-Redirect'] = str(full_path)
            if apache_xsendfile:
                response.headers['X-Sendfile'] = str(response.path)
            return response

    if gx_app.config.get('allowed_origin_hostnames', None):
        app.add_middleware(
            GalaxyCORSMiddleware,
            config=gx_app.config,
            allow_headers=["*"],
            allow_methods=["*"],
            max_age=600,
        )
    else:

        # handle CORS preflight requests - synchronize with wsgi behavior.
        @app.options('/api/{rest_of_path:path}')
        async def preflight_handler(request: Request, rest_of_path: str) -> Response:
            response = Response()
            response.headers['Access-Control-Allow-Headers'] = '*'
            response.headers['Access-Control-Max-Age'] = '600'
            return response


def initialize_fast_app(gx_wsgi_webapp, gx_app):
    app = FastAPI(
        title="Galaxy API",
        docs_url="/api/docs",
        openapi_tags=api_tags_metadata,
    )
    add_exception_handler(app)
    add_galaxy_middleware(app, gx_app)
    add_request_id_middleware(app)
    include_all_package_routers(app, 'galaxy.webapps.galaxy.api')
    wsgi_handler = WSGIMiddleware(gx_wsgi_webapp)
    app.mount('/', wsgi_handler)
    if gx_app.config.galaxy_url_prefix != '/':
        parent_app = FastAPI()
        parent_app.mount(gx_app.config.galaxy_url_prefix, app=app)
        return parent_app
    return app
