"""Module containing factory class for building uvicorn app for the Galaxy Tool Shed.

Information on uvicorn, its various settings, and how to invoke it can
be found at https://www.uvicorn.org/.

The Galaxy Tool Shed can be launched with uvicorn using the following invocation:

::

    uvicorn --app-dir lib --factory galaxy.webapps.reports.fast_factory:factory

Use the environment variable ``GALAXY_REPORTS_CONFIG`` to specify a Galaxy Reports
configuration file.

::

    GALAXY_REPORTS_CONFIG=config/reports.yml uvicorn --app-dir lib --factory galaxy.webapps.reports.fast_factory:factory

.. note::

    Information on additional ways to configure uvicorn can be found at
    https://www.uvicorn.org/.


`Gunicorn <https://docs.gunicorn.org/en/stable/index.html>`__ is a server with
more complex management options.

This factory function can be executed as a uvicorn worker managed with gunicorn
with the following command-line.

::

    gunicorn 'galaxy.webapps.reports.fast_factory:factory()' --env GALAXY_REPORTS_CONFIG=config/reports.yml --pythonpath lib -w 4 -k uvicorn.workers.UvicornWorker

"""

from galaxy.main_config import (
    WebappConfigResolver,
    WebappSetupProps,
)
from galaxy.webapps.reports.buildapp import app_factory
from .fast_app import initialize_fast_app


def factory():
    props = WebappSetupProps(
        app_name="reports",
        default_section_name="reports",
        env_config_file="GALAXY_REPORTS_CONFIG",
    )
    config_provider = WebappConfigResolver(props)
    config = config_provider.resolve_config()
    gx_webapp = app_factory(
        global_conf=config.global_conf, load_app_kwds=config.load_app_kwds, wsgi_preflight=config.wsgi_preflight
    )
    return initialize_fast_app(gx_webapp)
