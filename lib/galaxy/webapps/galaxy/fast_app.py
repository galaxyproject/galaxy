from fastapi import FastAPI, Request
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import JSONResponse
from pydantic.error_wrappers import ValidationError
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from galaxy.exceptions import MessageException
from galaxy.web.framework.decorators import api_error_message, validation_error_to_message_exception


def add_exception_handler(
    app: FastAPI
) -> None:

    @app.exception_handler(RequestValidationError)
    async def exception_middleware(request: Request, exc: MessageException) -> Response:
        exc = validation_error_to_message_exception(exc)
        error_dict = api_error_message(None, exception=exc)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_dict
        )

    @app.exception_handler(MessageException)
    async def exception_middleware(request: Request, exc: MessageException) -> Response:
        error_dict = api_error_message(None, exception=exc)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_dict
        )


def initialize_fast_app(gx_app, app=None):
    if app is None:
        app = FastAPI()

    add_exception_handler(app)
    wsgi_handler = WSGIMiddleware(gx_app)
    from galaxy.webapps.galaxy.api import jobs
    from galaxy.webapps.galaxy.api import roles
    app.include_router(jobs.router, prefix="/api/jobs")
    app.include_router(roles.router)
    app.mount('/', wsgi_handler)
    return app
