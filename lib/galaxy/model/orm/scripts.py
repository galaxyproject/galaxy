"""
Code to support database helper scripts (create_db.py, manage_db.py, etc...).
"""
import argparse
import logging
import os.path

from galaxy.util.path import get_ext
from galaxy.util.properties import find_config_file, load_app_properties
from galaxy.util.script import populate_config_args


log = logging.getLogger(__name__)

DEFAULT_CONFIG_NAMES = ['galaxy', 'universe_wsgi']
DEFAULT_CONFIG_PREFIX = ''
DEFAULT_DATABASE = 'galaxy'

DATABASE = {
    "galaxy":
        {
            'repo': 'lib/galaxy/model/migrate',
            'default_sqlite_file': './database/universe.sqlite',
            'config_override': 'GALAXY_CONFIG_',
        },
    "tools":
        {
            'repo': 'lib/tool_shed/galaxy_install/migrate',
            'default_sqlite_file': './database/universe.sqlite',
            'config_override': 'GALAXY_CONFIG_',
        },
    "tool_shed":
        {
            'repo': 'lib/galaxy/webapps/tool_shed/model/migrate',
            'config_names': ['tool_shed', 'tool_shed_wsgi'],
            'default_sqlite_file': './database/community.sqlite',
            'config_override': 'TOOL_SHED_CONFIG_',
            'config_section': 'tool_shed',
        },
    "install":
        {
            'repo': 'lib/galaxy/model/tool_shed_install/migrate',
            'config_prefix': 'install_',
            'default_sqlite_file': './database/install.sqlite',
            'config_override': 'GALAXY_INSTALL_CONFIG_',
        },
}


def _read_model_arguments(argv, use_argparse=False):
    if use_argparse:
        parser = argparse.ArgumentParser()
        parser.add_argument('database', metavar='DATABASE', type=str,
                            default="galaxy",
                            nargs='?',
                            help='database to target (galaxy, tool_shed, install)')
        populate_config_args(parser)
        args = parser.parse_args(argv[1:] if argv else [])
        return args.config_file, args.config_section, args.database
    else:
        config_file = None
        for arg in ["-c", "--config", "--config-file"]:
            if arg in argv:
                pos = argv.index(arg)
                argv.pop(pos)
                config_file = argv.pop(pos)
        config_section = None
        if "--config-section" in argv:
            pos = argv.index("--config-section")
            argv.pop(pos)
            config_section = argv.pop(pos)
        if argv and (argv[-1] in DATABASE):
            database = argv.pop()  # database name tool_shed, galaxy, or install.
        else:
            database = 'galaxy'
        return config_file, config_section, database


def get_config(argv, use_argparse=True, cwd=None):
    """
    Read sys.argv and parse out repository of migrations and database url.

    >>> import os
    >>> from six.moves.configparser import SafeConfigParser
    >>> from shutil import rmtree
    >>> from tempfile import mkdtemp
    >>> config_dir = mkdtemp()
    >>> os.makedirs(os.path.join(config_dir, 'config'))
    >>> def write_ini(path, property, value):
    ...     p = SafeConfigParser()
    ...     p.add_section('app:main')
    ...     p.set('app:main', property, value)
    ...     with open(os.path.join(config_dir, 'config', path), 'w') as f: p.write(f)
    >>> write_ini('tool_shed.ini', 'database_connection', 'sqlite:///pg/testdb1')
    >>> config = get_config(['manage_db.py', 'tool_shed'], cwd=config_dir)
    >>> config['repo']
    'lib/galaxy/webapps/tool_shed/model/migrate'
    >>> config['db_url']
    'sqlite:///pg/testdb1'
    >>> write_ini('galaxy.ini', 'database_file', 'moo.sqlite')
    >>> config = get_config(['manage_db.py'], cwd=config_dir)
    >>> config['db_url']
    'sqlite:///moo.sqlite?isolation_level=IMMEDIATE'
    >>> config['repo']
    'lib/galaxy/model/migrate'
    >>> rmtree(config_dir)
    """
    config_file, config_section, database = _read_model_arguments(argv, use_argparse=use_argparse)
    database_defaults = DATABASE[database]
    if config_file is None:
        config_names = database_defaults.get('config_names', DEFAULT_CONFIG_NAMES)
        if cwd:
            cwd = [cwd, os.path.join(cwd, 'config')]
        config_file = find_config_file(config_names, dirs=cwd)

    repo = database_defaults['repo']
    config_prefix = database_defaults.get('config_prefix', DEFAULT_CONFIG_PREFIX)
    config_override = database_defaults.get('config_override', 'GALAXY_CONFIG_')
    default_sqlite_file = database_defaults['default_sqlite_file']
    if config_section is None:
        if not config_file or get_ext(config_file, ignore='sample') == 'yaml':
            config_section = database_defaults.get('config_section', None)
        else:
            # Just use the default found by load_app_properties.
            config_section = None
    properties = load_app_properties(config_file=config_file, config_prefix=config_override, config_section=config_section)

    if ("%sdatabase_connection" % config_prefix) in properties:
        db_url = properties["%sdatabase_connection" % config_prefix]
    elif ("%sdatabase_file" % config_prefix) in properties:
        database_file = properties["%sdatabase_file" % config_prefix]
        db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % database_file
    else:
        db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % default_sqlite_file

    return dict(db_url=db_url, repo=repo, config_file=config_file, database=database)
