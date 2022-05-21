from a2wsgi import WSGIMiddleware
from fastapi import FastAPI

from galaxy.webapps.base.api import (
    add_exception_handler,
    add_request_id_middleware,
    include_all_package_routers,
)


def initialize_fast_app(gx_webapp, tool_shed_app):
    app = FastAPI(
        title="Galaxy Tool Shed API",
        description=("This API allows you to manage the Tool Shed repositories."),
        docs_url="/api/docs",
    )
    add_exception_handler(app)
    add_request_id_middleware(app)
    include_all_package_routers(app, "tool_shed.webapp.api")
    wsgi_handler = WSGIMiddleware(gx_webapp)
    tool_shed_app.haltables.append(("WSGI Middleware threadpool", wsgi_handler.executor.shutdown))
    app.mount("/", wsgi_handler)
    return app


__all__ = (
    "add_request_id_middleware",
    "initialize_fast_app",
)
