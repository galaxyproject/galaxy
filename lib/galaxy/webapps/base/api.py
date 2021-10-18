import logging

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.responses import Response
from starlette.routing import NoMatchFound

from galaxy.exceptions import MessageException
from galaxy.managers.base import ModelSerializer
from galaxy.web.framework import handle_uwsgi_url_for
try:
    from starlette_context.middleware import RawContextMiddleware
    from starlette_context.plugins import RequestIdPlugin
except ImportError:
    pass
from galaxy.web.framework.base import walk_controller_modules
from galaxy.web.framework.decorators import (
    api_error_message,
    validation_error_to_message_exception
)
from galaxy.webapps.galaxy.api import UrlBuilder

log = logging.getLogger(__name__)


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


def add_request_id_middleware(app: FastAPI):
    app.add_middleware(RawContextMiddleware, plugins=(RequestIdPlugin(force_new_uuid=True),))


def include_all_package_routers(app: FastAPI, package_name: str):
    for _, module in walk_controller_modules(package_name):
        router = getattr(module, "router", None)
        if router:
            app.include_router(router)


def get_url_builder(request: Request):
    return UrlBuilder(request)


def setup_reverse_url_lookup(app):
    """Makes all model serializers to use the ASGI URL builder by default.
    And fallback to UWSGI URL handling if the route is not registered.
    """

    def uses_dependency_injection(func):
        return app.magic_partial(func)

    @uses_dependency_injection
    def handle_asgi_url_for(*args, url_builder: UrlBuilder = Depends(get_url_builder), **kwargs) -> str:
        """Use the injected ASGI UrlBuilder to try and generate the URL.

        The name of the route must be registered correctly in the FastAPI route endpoint, otherwise it will
        fallback to the legacy UWSGI URL handling mechanism which in most cases will not work in ASGI context.
        """
        if url_builder:
            try:
                return url_builder(*args, **kwargs)
            except NoMatchFound:
                log.debug(f"No matching for route name: '{args[0]}'.")
                pass
        # Fallback to legacy url_for handling
        return handle_uwsgi_url_for(*args, **kwargs)

    ModelSerializer.url_for = handle_asgi_url_for
