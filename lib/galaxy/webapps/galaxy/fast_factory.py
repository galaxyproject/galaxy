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

    gunicorn 'galaxy.webapps.galaxy.fast_factory:factory()' --env GALAXY_CONFIG_FILE=config/galaxy.ini --pythonpath lib -w 4 -k uvicorn.workers.UvicornWorker

"""
import os

from galaxy.main_config import (
    absolute_config_path,
    config_is_ini,
    DEFAULT_CONFIG_SECTION,
    DEFAULT_INI_APP,
    find_config,
)
from galaxy.web_stack import get_app_kwds
from galaxy.webapps.galaxy.buildapp import app_pair
from .fast_app import initialize_fast_app


def factory():
    kwds = get_app_kwds("galaxy", "galaxy")
    config_file = kwds.get("config_file")
    if not config_file and "GALAXY_CONFIG_FILE" in os.environ:
        config_file = os.path.abspath(os.environ["GALAXY_CONFIG_FILE"])
    else:
        galaxy_root = kwds.get("galaxy_root")
        config_file = find_config(config_file, galaxy_root)
        config_file = absolute_config_path(config_file, galaxy_root=galaxy_root)

    if "GALAXY_CONFIG_SECTION" in os.environ:
        config_section = os.environ["GALAXY_CONFIG_SECTION"]
    elif config_is_ini(config_file):
        config_section = "app:%s" % DEFAULT_INI_APP
    else:
        config_section = DEFAULT_CONFIG_SECTION

    if 'config_file' not in kwds:
        kwds['config_file'] = config_file
    if 'config_section' not in kwds:
        kwds['config_section'] = config_section
    global_conf = {}
    if config_is_ini(config_file):
        global_conf["__file__"] = config_file
    gx_webapp, gx_app = app_pair(global_conf=global_conf, load_app_kwds=kwds, wsgi_preflight=False)
    return initialize_fast_app(gx_webapp, gx_app)
