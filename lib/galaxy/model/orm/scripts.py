"""
Code to support database helper scripts (create_db.py, manage_db.py, etc...).
"""
import logging

from galaxy.util.properties import find_config_file, load_app_properties


log = logging.getLogger( __name__ )

DEFAULT_CONFIG_FILE = 'config/galaxy.ini'
DEFAULT_CONFIG_PREFIX = ''
DEFAULT_DATABASE = 'galaxy'

DATABASE = {
    "galaxy":
        {
            'repo': 'lib/galaxy/model/migrate',
            'old_config_file': 'universe_wsgi.ini',
            'default_sqlite_file': './database/universe.sqlite',
            'config_override': 'GALAXY_CONFIG_',
        },
    "tool_shed":
        {
            'repo': 'lib/galaxy/webapps/tool_shed/model/migrate',
            'config_file': 'config/tool_shed.ini',
            'old_config_file': 'tool_shed_wsgi.ini',
            'default_sqlite_file': './database/community.sqlite',
            'config_override': 'TOOL_SHED_CONFIG_',
        },
    "install":
        {
            'repo': 'lib/galaxy/model/tool_shed_install/migrate',
            'old_config_file': 'universe_wsgi.ini',
            'config_prefix': 'install_',
            'default_sqlite_file': './database/install.sqlite',
            'config_override': 'GALAXY_INSTALL_CONFIG_',
        },
}


def read_config_file_arg( argv, default, old_default, cwd=None ):
    config_file = None
    if '-c' in argv:
        pos = argv.index( '-c' )
        argv.pop(pos)
        config_file = argv.pop( pos )

    return find_config_file( default, old_default, config_file, cwd=cwd )


def get_config( argv, cwd=None ):
    """
    Read sys.argv and parse out repository of migrations and database url.

    >>> import os
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
    config_file = read_config_file_arg( argv, default, old_default, cwd=cwd )
    repo = database_defaults[ 'repo' ]
    config_prefix = database_defaults.get( 'config_prefix', DEFAULT_CONFIG_PREFIX )
    config_override = database_defaults.get( 'config_override', 'GALAXY_CONFIG_' )
    default_sqlite_file = database_defaults[ 'default_sqlite_file' ]

    properties = load_app_properties( ini_file=config_file, config_prefix=config_override )

    if ("%sdatabase_connection" % config_prefix) in properties:
        db_url = properties[ "%sdatabase_connection" % config_prefix ]
    elif ("%sdatabase_file" % config_prefix) in properties:
        database_file = properties[ "%sdatabase_file" % config_prefix ]
        db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % database_file
    else:
        db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % default_sqlite_file

    return dict(db_url=db_url, repo=repo, config_file=config_file, database=database)
