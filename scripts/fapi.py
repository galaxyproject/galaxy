import uvicorn
from fastapi import FastAPI
from galaxy_main import (
    GalaxyConfigBuilder,
    main,
)

from galaxy.util.properties import load_app_properties
from galaxy.webapps.galaxy.buildapp import app_factory
from galaxy.webapps.galaxy.fast_app import initialize_fast_app

app = FastAPI()


def wsgiloop(args, log):
    config_builder = GalaxyConfigBuilder(args)
    kwds = config_builder.app_kwds()
    kwds = load_app_properties(**kwds)
    gx = app_factory(global_conf=config_builder.global_conf(), **kwds)
    initialize_fast_app(gx, app=app)
    uvicorn.run(app)


if __name__ == '__main__':
    main(wsgiloop)
