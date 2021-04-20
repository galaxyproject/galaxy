from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware


def initialize_fast_app(gx_webapp):
    app = FastAPI(
        title="Galaxy Tool Shed API",
        description=(
            "This API allows you to manage the Tool Shed repositories."
        ),
        docs_url="/api/docs",
    )
    wsgi_handler = WSGIMiddleware(gx_webapp)
    app.mount('/', wsgi_handler)
    return app
