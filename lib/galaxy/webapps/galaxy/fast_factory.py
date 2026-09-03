"""Module containing factory class for building uvicorn app for Galaxy.

Information on uvicorn, its various settings, and how to invoke it can
be found at https://www.uvicorn.org/.

Galaxy can be launched with uvicorn using the following invocation:

::

    uvicorn --app-dir lib --factory galaxy.webapps.galaxy.fast_factory:factory

Use the environment variable ``GALAXY_CONFIG_FILE`` to specify a Galaxy
configuration file. Galaxy configuration can be loading from a YAML
or an .ini file (reads app:main currently but can be overridden with
GALAXY_CONFIG_SECTION).

::

    GALAXY_CONFIG_FILE=config/galaxy.yml uvicorn --app-dir lib --factory galaxy.webapps.galaxy.fast_factory:factory

.. note::

    Information on additional ways to configure uvicorn can be found at
    https://www.uvicorn.org/.

.. warning::

    If an ini file is supplied via GALAXY_CONFIG_FILE, the server properties
    such as host and port are not read from the file like older forms of
    configuring Galaxy.

`Gunicorn <https://docs.gunicorn.org/en/stable/index.html>`__ is a server with
more complex management options.

This factory function can be executed as a uvicorn worker managed with gunicorn
with the following command-line.

::

    gunicorn 'galaxy.webapps.galaxy.fast_factory:factory()' --env GALAXY_CONFIG_FILE=config/galaxy.ini --pythonpath lib -w 4 -k uvicorn.workers.UvicornWorker --config lib/galaxy/web_stack/gunicorn_config.py

"""

from collections.abc import (
    Callable,
    Mapping,
)
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI

from galaxy.app import UniverseApplication as GalaxyUniverseApplication
from galaxy.main_config import (
    DEFAULT_CONFIG_SECTION,
    WebappConfigResolver,
    WebappSetupProps,
)
from galaxy.util.properties import load_app_properties
from galaxy.webapps.galaxy.buildapp import app_pair
from .fast_app import initialize_fast_app

FastAppFactory = Callable[[Any, GalaxyUniverseApplication], FastAPI]


@dataclass(frozen=True)
class GalaxyWebApp:
    """The application objects assembled for a Galaxy web process."""

    galaxy_app: GalaxyUniverseApplication
    wsgi_app: Any
    asgi_app: FastAPI


def build_galaxy_web_app(
    galaxy_config: Mapping[str, Any] | None = None,
    *,
    global_conf: Mapping[str, Any] | None = None,
    load_app_kwds: Mapping[str, Any] | None = None,
    wsgi_preflight: bool = False,
    register_shutdown_at_exit: bool = True,
    init_fast_app: FastAppFactory = initialize_fast_app,
) -> GalaxyWebApp:
    """Build Galaxy's application objects from programmatic configuration.

    Unlike the uvicorn ``factory`` below, this entry point does not require a
    configuration file or environment-variable setup. It also returns the
    underlying Galaxy application so embedding callers can own its lifecycle.
    Application construction exceptions are allowed to propagate to the caller.
    """
    global_conf_dict = dict(global_conf or {})
    app_kwds = load_app_properties(kwds=dict(galaxy_config or {}), **dict(load_app_kwds or {}))
    app_kwds["register_shutdown_at_exit"] = register_shutdown_at_exit

    galaxy_app = GalaxyUniverseApplication(global_conf=global_conf_dict, is_webapp=True, **app_kwds)
    try:
        wsgi_app, paired_galaxy_app = app_pair(
            global_conf_dict,
            app=galaxy_app,
            wsgi_preflight=wsgi_preflight,
            **app_kwds,
        )
        assert paired_galaxy_app is galaxy_app
        asgi_app = init_fast_app(wsgi_app, galaxy_app)
    except Exception:
        with suppress(Exception):
            galaxy_app.shutdown()
        raise
    return GalaxyWebApp(galaxy_app=galaxy_app, wsgi_app=wsgi_app, asgi_app=asgi_app)


def factory():
    props = WebappSetupProps(
        app_name="galaxy",
        default_section_name=DEFAULT_CONFIG_SECTION,
        env_config_file="GALAXY_CONFIG_FILE",
        env_config_section="GALAXY_CONFIG_SECTION",
        check_galaxy_root=True,
    )
    config_provider = WebappConfigResolver(props)
    config = config_provider.resolve_config()
    web_app = build_galaxy_web_app(
        global_conf=config.global_conf,
        load_app_kwds=config.load_app_kwds,
        wsgi_preflight=config.wsgi_preflight,
    )
    return web_app.asgi_app
