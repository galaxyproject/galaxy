import uvicorn
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from galaxy_main import (
    GalaxyConfigBuilder,
    main,
)

from galaxy.util.properties import load_app_properties
from galaxy.webapps.galaxy.buildapp import app_factory

app = FastAPI()


def wsgiloop(args, log):
    config_builder = GalaxyConfigBuilder(args)
    kwds = config_builder.app_kwds()
    kwds = load_app_properties(**kwds)
    gx = app_factory(global_conf=config_builder.global_conf(), **kwds)
    wsgi_handler = WSGIMiddleware(gx)

    # app factory will import api controllers while passing in app object,
    # this needs to happen before we can import the router from individual api modules
    # (until we've replaced everything with FastAPI, at which point we can do normal imports).
    from galaxy.webapps.galaxy.api import jobs
    app.include_router(jobs.router, prefix='/api/jobs')
    app.mount('/', wsgi_handler)
    uvicorn.run(app)


if __name__ == '__main__':
    main(wsgiloop)
