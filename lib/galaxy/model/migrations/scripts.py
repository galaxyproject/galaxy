import os
from collections import namedtuple

from galaxy.util.properties import (
    find_config_file,
    get_data_dir,
    load_app_properties,
)

DEFAULT_CONFIG_NAMES = ['galaxy', 'universe_wsgi']
CONFIG_FILE_ARG = '--galaxy-config'
CONFIG_DIR_NAME = 'config'
GXY_CONFIG_PREFIX = 'GALALXY_CONFIG_'
TSI_CONFIG_PREFIX = 'GALALXY_INSTALL_CONFIG_'

DatabaseConfig = namedtuple('DatabaseConfig', ['url', 'template', 'encoding'])


def _pop_config_file(argv):
    if CONFIG_FILE_ARG in argv:
        pos = argv.index(CONFIG_FILE_ARG)
        argv.pop(pos)  # pop argument name
        return argv.pop(pos)  # pop and return argument value


def get_configuration(argv, cwd) -> tuple[DatabaseConfig, DatabaseConfig, bool]:
    """
    Return a 3-item-tuple with configuration values used for managing databases.
    """
    config_file = _pop_config_file(argv)
    if config_file is None:
        cwds = [cwd, os.path.join(cwd, CONFIG_DIR_NAME)]
        config_file = find_config_file(DEFAULT_CONFIG_NAMES, dirs=cwds)

    # load gxy properties and auto-migrate
    properties = load_app_properties(config_file=config_file, config_prefix=GXY_CONFIG_PREFIX)
    default_url = f"sqlite:///{os.path.join(get_data_dir(properties), 'universe.sqlite')}?isolation_level=IMMEDIATE"
    url = properties.get('database_connection', default_url)
    template = properties.get('database_template', None)
    encoding = properties.get('database_encoding', None)
    is_auto_migrate = properties.get('database_auto_migrate', False)
    gxy_config = DatabaseConfig(url, template, encoding)

    # load tsi properties
    properties = load_app_properties(config_file=config_file, config_prefix=TSI_CONFIG_PREFIX)
    default_url = gxy_config.url
    url = properties.get('install_database_connection', default_url)
    template = properties.get('database_template', None)
    encoding = properties.get('database_encoding', None)
    tsi_config = DatabaseConfig(url, template, encoding)

    return (gxy_config, tsi_config, is_auto_migrate)
