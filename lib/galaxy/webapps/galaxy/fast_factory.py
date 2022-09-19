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

from galaxy.main_config import (
    DEFAULT_CONFIG_SECTION,
    WebappConfigResolver,
    WebappSetupProps,
)
from galaxy.webapps.galaxy.buildapp import app_pair
from .fast_app import initialize_fast_app


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
    gx_wsgi_webapp, gx_app = app_pair(
        global_conf=config.global_conf, load_app_kwds=config.load_app_kwds, wsgi_preflight=config.wsgi_preflight
    )
    return initialize_fast_app(gx_wsgi_webapp, gx_app)
