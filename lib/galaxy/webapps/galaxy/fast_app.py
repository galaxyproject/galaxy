from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

from galaxy.exceptions import MessageException
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
    from galaxy.webapps.galaxy.api import (
        datatypes,
        job_lock,
        jobs,
        roles,
        licenses
    )
    app.include_router(datatypes.router)
    app.include_router(jobs.router)
    app.include_router(job_lock.router)
    app.include_router(roles.router)
    app.include_router(licenses.router)
    app.mount('/', wsgi_handler)
    return app
