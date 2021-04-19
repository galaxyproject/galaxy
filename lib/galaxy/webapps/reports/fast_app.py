from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware


def initialize_fast_app(gx_webapp):
    app = FastAPI()
    wsgi_handler = WSGIMiddleware(gx_webapp)
    app.mount('/', wsgi_handler)
    return app
