import json

from galaxy_main import (
    GalaxyConfigBuilder,
    main,
)
from aiohttp import web, WSMsgType  # noqa: I100
from aiohttp_wsgi import WSGIHandler

from galaxy.util.properties import load_app_properties
from galaxy.webapps.galaxy.api import tools
from galaxy.webapps.galaxy.buildapp import app_factory
from galaxy.work.context import WorkRequestContext


def aiohttp_loop(args, log):
    config_builder = GalaxyConfigBuilder(args)
    kwds = config_builder.app_kwds()
    kwds = load_app_properties(**kwds)
    gx = app_factory(global_conf=config_builder.global_conf(), **kwds)
    wsgi_handler = WSGIHandler(gx)
    app = web.Application()
    app['websockets'] = []
    routes = web.RouteTableDef()

    @routes.get('/hello')
    async def hello(request):
        return web.Response(text="Hello, world")
    
    @routes.get('/ws')
    async def ws(request):
        ws = web.WebSocketResponse()

        # track websockets for the fun of it
        request.app['websockets'].append(ws)
        await ws.prepare(request)
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                else:
                    from galaxy.app import app as galaxy_app
                    tc = tools.ToolsController(galaxy_app)
                    user = galaxy_app.model.session.query(galaxy_app.model.User).get(1)
                    trans = WorkRequestContext(galaxy_app, user=user, ws=ws)
                    payload = json.loads(msg.data)
                    tc._create(trans=trans, payload=payload)
                    # Respond to all sockets, otherwise just respond to ws
                    await ws.send_str(msg.data + '/answer')
            elif msg.type == WSMsgType.ERROR:
                print('ws connection closed with exception %s' %
                      ws.exception())

        print('websocket connection closed')
        return ws

    app.add_routes(routes)
    app.router.add_route("*", "/{path_info:.*}", wsgi_handler)
    web.run_app(app)


if __name__ == "__main__":
    main(aiohttp_loop)
