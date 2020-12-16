from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware


def initialize_fast_app(gx_app, app=None):
    if app is None:
        app = FastAPI()
    wsgi_handler = WSGIMiddleware(gx_app)
    from galaxy.webapps.galaxy.api import jobs
    from galaxy.webapps.galaxy.api import roles
    app.include_router(jobs.router, prefix='/api/jobs')
    app.include_router(roles.router, prefix='/api/roles')
    app.mount('/', wsgi_handler)
    return app
