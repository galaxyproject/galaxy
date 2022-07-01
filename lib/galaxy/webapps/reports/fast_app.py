from a2wsgi import WSGIMiddleware
from fastapi import FastAPI

from galaxy.webapps.base.api import (
    add_empty_response_middleware,
    add_exception_handler,
    add_request_id_middleware,
    include_all_package_routers,
)


def initialize_fast_app(gx_webapp):
    app = FastAPI(
        title="Galaxy Reports API",
        description=(
            "This API will give you insights into the Galaxy instance's usage and load. "
            "It aims to provide data about users, jobs, workflows, disk space, and much more."
        ),
        docs_url="/api/docs",
    )
    add_exception_handler(app)
    add_request_id_middleware(app)
    include_all_package_routers(app, "galaxy.webapps.reports.api")
    wsgi_handler = WSGIMiddleware(gx_webapp)
    app.mount("/", wsgi_handler)
    add_empty_response_middleware(app)
    return app
