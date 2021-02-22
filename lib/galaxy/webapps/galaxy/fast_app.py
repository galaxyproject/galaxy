from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
try:
    from starlette_context.middleware import RawContextMiddleware
    from starlette_context.plugins import RequestIdPlugin
except ImportError:
    pass

from galaxy.exceptions import MessageException
from galaxy.web.framework.base import walk_controller_modules
from galaxy.web.framework.decorators import (
    api_error_message,
    validation_error_to_message_exception
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


def add_exception_handler(
    app: FastAPI
) -> None:

    @app.exception_handler(RequestValidationError)
    async def validate_exception_middleware(request: Request, exc: RequestValidationError) -> Response:
        exc = validation_error_to_message_exception(exc)
        error_dict = api_error_message(None, exception=exc)
        return JSONResponse(
            status_code=400,
            content=error_dict
        )

    @app.exception_handler(MessageException)
    async def message_exception_middleware(request: Request, exc: MessageException) -> Response:
        error_dict = api_error_message(None, exception=exc)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_dict
        )


def add_galaxy_middleware(app: FastAPI, gx_app):
    x_frame_options = getattr(gx_app.config, 'x_frame_options', None)
    if x_frame_options:

        @app.middleware("http")
        async def add_x_frame_options(request: Request, call_next):
            response = await call_next(request)
            response.headers['X-Frame-Options'] = x_frame_options
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


def add_request_id_middleware(app: FastAPI):
    app.add_middleware(RawContextMiddleware, plugins=(RequestIdPlugin(force_new_uuid=True),))


def initialize_fast_app(gx_webapp, gx_app):
    app = FastAPI(
        openapi_tags=api_tags_metadata
    )
    add_exception_handler(app)
    add_galaxy_middleware(app, gx_app)
    add_request_id_middleware(app)
    wsgi_handler = WSGIMiddleware(gx_webapp)
    for _, module in walk_controller_modules('galaxy.webapps.galaxy.api'):
        router = getattr(module, "router", None)
        if router:
            app.include_router(router)
    app.mount('/', wsgi_handler)
    return app
