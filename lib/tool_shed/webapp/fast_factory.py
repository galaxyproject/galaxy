import os

from galaxy.util.properties import find_config_file
from galaxy.web_stack import get_app_kwds
from tool_shed.webapp.buildapp import app_factory
from .fast_app import initialize_fast_app

APP_NAME = "tool_shed"


def factory():
    kwds = get_app_kwds(APP_NAME, APP_NAME)
    config_file = kwds.get("config_file")
    if not config_file and os.environ.get('TOOL_SHED_CONFIG_FILE'):
        config_file = os.path.abspath(os.environ["TOOL_SHED_CONFIG_FILE"])
    else:
        config_file = find_config_file([APP_NAME])

    config_section = APP_NAME

    if 'config_file' not in kwds:
        kwds['config_file'] = config_file
    if 'config_section' not in kwds:
        kwds['config_section'] = config_section
    global_conf = {}
    gx_webapp = app_factory(global_conf=global_conf, load_app_kwds=kwds, wsgi_preflight=False)
    return initialize_fast_app(gx_webapp)
