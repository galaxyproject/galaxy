import os
import re
from typing import (
    List,
    NamedTuple,
    Optional,
    Tuple,
)

from galaxy.util.properties import (
    find_config_file,
    get_data_dir,
    load_app_properties,
)

DEFAULT_CONFIG_NAMES = ['galaxy', 'universe_wsgi']
CONFIG_FILE_ARG = '--galaxy-config'
CONFIG_DIR_NAME = 'config'
GXY_CONFIG_PREFIX = 'GALAXY_CONFIG_'
TSI_CONFIG_PREFIX = 'GALAXY_INSTALL_CONFIG_'


class DatabaseConfig(NamedTuple):
    url: str
    template: str
    encoding: str


def _pop_config_file(argv: List[str]) -> Optional[str]:
    if CONFIG_FILE_ARG in argv:
        pos = argv.index(CONFIG_FILE_ARG)
        argv.pop(pos)  # pop argument name
        return argv.pop(pos)  # pop and return argument value
    return None


def get_configuration(argv: List[str], cwd: str) -> Tuple[DatabaseConfig, DatabaseConfig, bool]:
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


def add_db_urls_to_command_arguments(argv: List[str], cwd: str) -> None:
    gxy_config, tsi_config, _ = get_configuration(argv, cwd)
    _insert_x_argument(argv, 'tsi_url', tsi_config.url)
    _insert_x_argument(argv, 'gxy_url', gxy_config.url)


def _insert_x_argument(argv, key: str, value: str) -> None:
    # `_insert_x_argument('mykey', 'myval')` transforms `foo -a 1` into `foo -x mykey=myval -a 42`
    argv.insert(1, f'{key}={value}')
    argv.insert(1, '-x')


class LegacyScripts:

    LEGACY_CONFIG_FILE_ARG_NAMES = ['-c', '--config', '--config-file']
    ALEMBIC_CONFIG_FILE_ARG = '--alembic-config'  # alembic config file, set in the calling script

    def pop_database_argument(self, argv: List[str]) -> str:
        """
        If last argument is a valid database name, pop and return it; otherwise return default.
        """
        arg = argv[-1]
        if arg in ['galaxy', 'install']:
            return argv.pop()
        return 'galaxy'

    def rename_config_argument(self, argv: List[str]) -> None:
        """
        Rename the optional config argument: we can't use '-c' because that option is used by Alembic.
        """
        for arg in self.LEGACY_CONFIG_FILE_ARG_NAMES:
            if arg in argv:
                self._rename_arg(argv, arg, CONFIG_FILE_ARG)
                return

    def rename_alembic_config_argument(self, argv: List[str]) -> None:
        """
        Rename argument name: `--alembic-config` to `-c`. There should be no `-c` argument present.
        """
        if '-c' in argv:
            raise Exception('Cannot rename alembic config argument: `-c` argument present.')
        self._rename_arg(argv, self.ALEMBIC_CONFIG_FILE_ARG, '-c')

    def convert_version_argument(self, argv: List[str], database: str) -> None:
        """
        Convert legacy version argument to current spec required by Alembic.
        """
        if '--version' in argv:
            # Just remove it: the following argument should be the version/revision identifier.
            pos = argv.index('--version')
            argv.pop(pos)
        else:
            # If we find --version=foo, extract foo and replace arg with foo (which is the revision identifier)
            p = re.compile(r'--version=([0-9A-Fa-f]+)')
            for i, arg in enumerate(argv):
                m = p.match(arg)
                if m:
                    argv[i] = m.group(1)
                    return
            # No version argumen found: construct branch@head argument for an upgrade operation.
            # Raise exception otherwise.
            if 'upgrade' not in argv:
                raise Exception('If no `--version` argument supplied, `upgrade` argument is requried')

            if database == 'galaxy':
                argv.append('gxy@head')
            elif database == 'install':
                argv.append('tsi@head')

    def _rename_arg(self, argv, old_name, new_name) -> None:
        pos = argv.index(old_name)
        argv[pos] = new_name
