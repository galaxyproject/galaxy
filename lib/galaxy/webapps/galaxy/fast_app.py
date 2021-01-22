from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

from galaxy.exceptions import MessageException
from galaxy.web.framework.base import walk_controller_modules
from galaxy.web.framework.decorators import (
    api_error_message,
    validation_error_to_message_exception
)

# https://fastapi.tiangolo.com/tutorial/metadata/#metadata-for-tags
api_tags_metadata = [
    {
        "name": "datatypes",
        "description": "Operations with supported data types.",
    },
    {
        "name": "licenses",
        "description": "Operations with [SPDX licenses](https://spdx.org/licenses/).",
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


def add_exception_handler(
    app: FastAPI
) -> None:

    @app.exception_handler(RequestValidationError)
    async def validate_exception_middleware(request: Request, exc: MessageException) -> Response:
        exc = validation_error_to_message_exception(exc)
        error_dict = api_error_message(None, exception=exc)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_dict
        )

    @app.exception_handler(MessageException)
    async def message_exception_middleware(request: Request, exc: MessageException) -> Response:
        error_dict = api_error_message(None, exception=exc)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_dict
        )


def initialize_fast_app(gx_app):
    app = FastAPI(openapi_tags=api_tags_metadata)

    add_exception_handler(app)
    wsgi_handler = WSGIMiddleware(gx_app)
    for _, module in walk_controller_modules('galaxy.webapps.galaxy.api'):
        router = getattr(module, "router", None)
        if router:
            app.include_router(router)
    app.mount('/', wsgi_handler)
    return app
