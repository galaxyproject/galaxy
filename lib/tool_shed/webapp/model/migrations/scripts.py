import os
from typing import (
    List,
    Optional,
)

from galaxy.model.migrations.base import pop_arg_from_args
from galaxy.util.properties import (
    find_config_file,
    get_data_dir,
    load_app_properties,
)

DEFAULT_CONFIG_NAMES = ["tool_shed", "tool_shed_wsgi"]
CONFIG_FILE_ARG = "--toolshed-config"
CONFIG_DIR_NAME = "config"
TOOLSHED_CONFIG_PREFIX = "TOOL_SHED_CONFIG_"


def get_dburl(argv: List[str], cwd: str) -> str:
    """Return db url."""
    config_file = pop_arg_from_args(argv, CONFIG_FILE_ARG)
    return get_dburl_from_file(cwd, config_file)


def get_dburl_from_file(cwd: str, config_file: Optional[str] = None) -> str:
    if config_file is None:
        cwds = [cwd, os.path.join(cwd, CONFIG_DIR_NAME)]
        config_file = find_config_file(DEFAULT_CONFIG_NAMES, dirs=cwds)

    properties = load_app_properties(config_file=config_file, config_prefix=TOOLSHED_CONFIG_PREFIX)
    default_url = f"sqlite:///{os.path.join(get_data_dir(properties), 'community.sqlite')}?isolation_level=IMMEDIATE"
    url = properties.get("database_connection", default_url)
    return url
