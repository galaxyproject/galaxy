from galaxy_main import (
    GalaxyConfigBuilder,
    main,
)
from aiohttp import web  # noqa: I100
from aiohttp_wsgi import WSGIHandler

from galaxy.util.properties import load_app_properties
from galaxy.webapps.galaxy.buildapp import app_factory


def aiohttp_loop(args, log):
    config_builder = GalaxyConfigBuilder(args)
    kwds = config_builder.app_kwds()
    kwds = load_app_properties(**kwds)
    gx = app_factory(global_conf=config_builder.global_conf(), **kwds)
    wsgi_handler = WSGIHandler(gx)
    app = web.Application()
    routes = web.RouteTableDef()

    @routes.get('/hello')
    async def hello(request):
        return web.Response(text="Hello, world")

    app.add_routes(routes)
    app.router.add_route("*", "/{path_info:.*}", wsgi_handler)
    web.run_app(app)


if __name__ == "__main__":
    main(aiohttp_loop)
