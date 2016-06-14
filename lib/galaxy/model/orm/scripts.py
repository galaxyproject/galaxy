"""
Code to support database helper scripts (create_db.py, manage_db.py, etc...).
"""
import logging
import os
import sys

from migrate.versioning.shell import main as migrate_main

from galaxy.util.properties import load_app_properties, get_data_dir, running_from_source


log = logging.getLogger( __name__ )

DEFAULT_CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'config', 'sample'))
DEFAULT_CONFIG_FILE = 'config/galaxy.ini'
DEFAULT_CONFIG_PREFIX = ''
DEFAULT_DATABASE = 'galaxy'

DATABASE = {
    "galaxy":
        {
            'repo': 'galaxy/model/migrate',
            'old_config_file': 'universe_wsgi.ini',
            'default_sqlite_file': 'universe.sqlite',
            'config_override': 'GALAXY_CONFIG_',
        },
    "tool_shed":
        {
            'repo': 'galaxy/webapps/tool_shed/model/migrate',
            'config_file': 'config/tool_shed.ini',
            'old_config_file': 'tool_shed_wsgi.ini',
            'default_sqlite_file': 'community.sqlite',
            'config_override': 'TOOL_SHED_CONFIG_',
        },
    "install":
        {
            'repo': 'galaxy/model/tool_shed_install/migrate',
            'old_config_file': 'universe_wsgi.ini',
            'config_prefix': 'install_',
            'default_sqlite_file': 'install.sqlite',
            'config_override': 'GALAXY_INSTALL_CONFIG_',
        },
}


def read_config_file_arg( argv, default, old_default ):
    config_file = None
    if '-c' in argv:
        pos = argv.index( '-c' )
        argv.pop(pos)
        config_file = argv.pop( pos )
    elif not running_from_source:
        if os.path.exists( os.path.basename( default ) ):
            config_file = os.path.basename( default )
    else:
        if not os.path.exists( default ) and os.path.exists( old_default ):
            config_file = old_default
        elif os.path.exists( default ):
            config_file = default
    if config_file is None:
        config_file = os.path.join( DEFAULT_CONFIG_DIR, os.path.basename( default ) + ".sample" )
    return config_file


def get_config( argv, cwd=None ):
    """
    Read sys.argv and parse out repository of migrations and database url.

    >>> from ConfigParser import SafeConfigParser
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
    """
    if argv and (argv[-1] in DATABASE):
        database = argv.pop()  # database name tool_shed, galaxy, or install.
    else:
        database = 'galaxy'
    database_defaults = DATABASE[ database ]

    default = database_defaults.get( 'config_file', DEFAULT_CONFIG_FILE )
    old_default = database_defaults.get( 'old_config_file' )
    if cwd is not None:
        default = os.path.join( cwd, default )
        old_default = os.path.join( cwd, old_default )
    config_file = read_config_file_arg( argv, default, old_default )
    repo = os.path.join( os.path.dirname( __file__ ), os.pardir, os.pardir, os.pardir, database_defaults[ 'repo' ] )
    config_prefix = database_defaults.get( 'config_prefix', DEFAULT_CONFIG_PREFIX )
    config_override = database_defaults.get( 'config_override', 'GALAXY_CONFIG_' )
    default_sqlite_file = database_defaults[ 'default_sqlite_file' ]
    if cwd:
        config_file = os.path.join( cwd, config_file )

    properties = load_app_properties( ini_file=config_file, config_prefix=config_override )

    if ("%sdatabase_connection" % config_prefix) in properties:
        db_url = properties[ "%sdatabase_connection" % config_prefix ]
    else:
        db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % os.path.join(get_data_dir(properties), default_sqlite_file)

    return dict(db_url=db_url, repo=repo, config_file=config_file, database=database)


def manage_db():
    config = get_config(sys.argv)
    migrate_main(repository=config['repo'], url=config['db_url'])
