import os
import stat
import typing
from pathlib import Path
from typing import cast

import anyio
from fastapi import FastAPI, Request
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import (
    FileResponse,
    RedirectResponse,
    Response,
)
from starlette.staticfiles import PathLike
from starlette.types import Scope

from galaxy.webapps.base.api import (
    add_exception_handler,
    add_request_id_middleware,
    include_all_package_routers,
)
from galaxy.webapps.base.webapp import config_allows_origin

if typing.TYPE_CHECKING:
    from galaxy.config import Configuration

# https://fastapi.tiangolo.com/tutorial/metadata/#metadata-for-tags
api_tags_metadata = [
    {
        "name": "configuration",
        "description": "Configuration-related endpoints.",
    },
    {
        "name": "datatypes",
        "description": "Operations with supported data types.",
    },
    {
        "name": "genomes",
        "description": "Operations with genome data.",
    },
    {
        "name": "group_roles",
        "description": "Operations with group roles.",
    },
    {
        "name": "licenses",
        "description": "Operations with [SPDX licenses](https://spdx.org/licenses/).",
    },
    {
        "name": "tags",
        "description": "Operations with tags.",
    },
    {
        "name": "tool data tables",
        "description": "Operations with tool [Data Tables](https://galaxyproject.org/admin/tools/data-tables/).",
    },
    {
        "name": "tours",
        "description": "Operations with interactive tours.",
    },
    {
        "name": "remote files",
        "description": "Operations with remote dataset sources.",
    },
]


def get_static_from_config(conf, option_name, default_path):
    config_val = conf.get(option_name, default_path)
    per_host_config_option = f"{option_name}_by_host"
    per_host_config = conf.get(per_host_config_option)
    return (config_val, per_host_config or {})


class GalaxyStaticFiles(StaticFiles):
    def __init__(
        self, *, config: "Configuration", html: bool = False, check_dir: bool = True
    ) -> None:
        self.config = config
        self.directory, self.directory_per_host = get_static_from_config(
            config, "static_dir", "static/"
        )
        super().__init__(
            directory=self.directory, packages=None, html=html, check_dir=check_dir
        )

    def get_directories(
        self, directory: PathLike = None, packages: typing.List[str] = None
    ) -> typing.List[PathLike]:
        pass

    async def check_config(self) -> None:
        """
        Perform a one-off configuration check that GalaxyStaticFiles is actually
        pointed at directories, so that we can raise loud errors rather than
        just returning 404 responses.
        """
        for directory in (self.directory, *self.directory_per_host.values()):
            try:
                stat_result = await anyio.to_thread.run_sync(os.stat, directory)
            except FileNotFoundError:
                raise RuntimeError(
                    f"StaticFiles directory '{directory}' does not exist."
                )
            if not (
                stat.S_ISDIR(stat_result.st_mode) or stat.S_ISLNK(stat_result.st_mode)
            ):
                raise RuntimeError(
                    f"StaticFiles path '{directory}' is not a directory."
                )

    async def get_response(self, path: str, scope: Scope) -> Response:
        """
        Returns an HTTP response, given the incoming path, method and request headers.
        """
        if scope["method"] not in ("GET", "HEAD"):
            raise HTTPException(status_code=405)

        headers = Headers(scope=scope)

        try:
            full_path, stat_result = await anyio.to_thread.run_sync(
                self._lookup_path, path, headers.get("host")
            )
        except PermissionError:
            raise HTTPException(status_code=401)
        except OSError:
            raise

        if stat_result and stat.S_ISREG(stat_result.st_mode):
            # We have a static file to serve.
            return self.file_response(full_path, stat_result, scope)

        raise HTTPException(status_code=404)

    def _lookup_path(
        self, path: str, host: typing.Optional[str] = None
    ) -> typing.Tuple[str, typing.Optional[os.stat_result]]:
        directory = self.directory_per_host.get(host, self.directory)
        full_path = os.path.realpath(os.path.join(directory, path))
        directory = os.path.realpath(directory)
        if os.path.commonprefix([full_path, directory]) != directory:
            # Don't allow misbehaving clients to break out of the static files
            # directory.
            return "", None
        try:
            return full_path, os.stat(full_path)
        except (FileNotFoundError, NotADirectoryError):
            return "", None


class GalaxyCORSMiddleware(CORSMiddleware):

    def __init__(self, *args, **kwds):
        self.config = kwds.pop("config")
        super().__init__(*args, **kwds)

    def is_allowed_origin(self, origin: str) -> bool:
        return config_allows_origin(origin, self.config)


def add_galaxy_middleware(app: FastAPI, gx_app):
    x_frame_options = gx_app.config.x_frame_options
    if x_frame_options:

        @app.middleware("http")
        async def add_x_frame_options(request: Request, call_next):
            response = await call_next(request)
            response.headers['X-Frame-Options'] = x_frame_options
            return response

    nginx_x_accel_redirect_base = gx_app.config.nginx_x_accel_redirect_base
    apache_xsendfile = gx_app.config.apache_xsendfile

    if gx_app.config.sentry_dsn:
        from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
        app.add_middleware(SentryAsgiMiddleware)

    if nginx_x_accel_redirect_base or apache_xsendfile:

        @app.middleware("http")
        async def add_send_file_header(request: Request, call_next) -> Response:
            response = await call_next(request)
            if not isinstance(response, FileResponse):
                return response
            response = cast(FileResponse, response)
            if nginx_x_accel_redirect_base:
                full_path = Path(nginx_x_accel_redirect_base) / response.path
                response.headers['X-Accel-Redirect'] = str(full_path)
            if apache_xsendfile:
                response.headers['X-Sendfile'] = str(response.path)
            return response

    if gx_app.config.get('allowed_origin_hostnames', None):
        app.add_middleware(
            GalaxyCORSMiddleware,
            config=gx_app.config,
            allow_headers=["*"],
            allow_methods=["*"],
            max_age=600,
        )
    else:

        # handle CORS preflight requests - synchronize with wsgi behavior.
        @app.options('/api/{rest_of_path:path}')
        async def preflight_handler(request: Request, rest_of_path: str) -> Response:
            response = Response()
            response.headers['Access-Control-Allow-Headers'] = '*'
            response.headers['Access-Control-Max-Age'] = '600'
            return response


def initialize_fast_app(gx_wsgi_webapp, gx_app):
    app = FastAPI(
        title="Galaxy API",
        docs_url="/api/docs",
        openapi_tags=api_tags_metadata,
    )
    add_exception_handler(app)
    add_galaxy_middleware(app, gx_app)
    add_request_id_middleware(app)
    include_all_package_routers(app, 'galaxy.webapps.galaxy.api')
    # app.mount("/static", GalaxyStaticFiles(config=gx_app.config), name="static")

    @app.get("/favicon.ico")
    async def favicon():
        return RedirectResponse(url="static/favicon.ico")

    wsgi_handler = WSGIMiddleware(gx_wsgi_webapp)
    app.mount('/', wsgi_handler)
    if gx_app.config.galaxy_url_prefix != '/':
        parent_app = FastAPI()
        parent_app.mount(gx_app.config.galaxy_url_prefix, app=app)
        return parent_app
    return app
