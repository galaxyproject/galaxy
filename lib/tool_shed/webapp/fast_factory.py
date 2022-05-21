"""Module containing factory class for building uvicorn app for the Galaxy Tool Shed.

Information on uvicorn, its various settings, and how to invoke it can
be found at https://www.uvicorn.org/.

The Galaxy Tool Shed can be launched with uvicorn using the following invocation:

::

    uvicorn --app-dir lib --factory tool_shed.webapp.fast_factory:factory

Use the environment variable ``TOOL_SHED_CONFIG_FILE`` to specify a Tool Shed
configuration file.

::

    TOOL_SHED_CONFIG_FILE=config/tool_shed.yml uvicorn --app-dir lib --factory tool_shed.webapp.fast_factory:factory

.. note::

    Information on additional ways to configure uvicorn can be found at
    https://www.uvicorn.org/.


`Gunicorn <https://docs.gunicorn.org/en/stable/index.html>`__ is a server with
more complex management options.

This factory function can be executed as a uvicorn worker managed with gunicorn
with the following command-line.

::

    gunicorn 'tool_shed.webapp.fast_factory:factory()' --env TOOL_SHED_CONFIG_FILE=config/tool_shed.yml --pythonpath lib -w 4 -k uvicorn.workers.UvicornWorker --config lib/galaxy/web_stack/gunicorn_config.py

"""

from galaxy.main_config import (
    WebappConfigResolver,
    WebappSetupProps,
)
from tool_shed.webapp.buildapp import app_pair
from tool_shed.webapp.config import TOOLSHED_APP_NAME
from .fast_app import initialize_fast_app


def factory():
    props = WebappSetupProps(
        app_name=TOOLSHED_APP_NAME,
        default_section_name=TOOLSHED_APP_NAME,
        env_config_file="TOOL_SHED_CONFIG_FILE",
    )
    config_provider = WebappConfigResolver(props)
    config = config_provider.resolve_config()
    gx_webapp, app = app_pair(
        global_conf=config.global_conf, load_app_kwds=config.load_app_kwds, wsgi_preflight=config.wsgi_preflight
    )
    return initialize_fast_app(gx_webapp, app)
