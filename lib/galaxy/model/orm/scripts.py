"""
Code to support database helper scripts (create_db.py, manage_db.py, etc...).
"""
import logging
import os.path
from ConfigParser import SafeConfigParser

from galaxy import eggs

eggs.require( "decorator" )
eggs.require( "Tempita" )
eggs.require( "SQLAlchemy" )
eggs.require( "sqlalchemy_migrate" )

from galaxy.model.orm import dialect_to_egg

import pkg_resources

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
        },
    "tool_shed":
        {
            'repo':  'lib/galaxy/webapps/tool_shed/model/migrate',
            'config_file': 'config/tool_shed.ini',
            'old_config_file': 'tool_shed_wsgi.ini',
            'default_sqlite_file': './database/community.sqlite',
        },
    "install":
        {
            'repo': 'lib/galaxy/model/tool_shed_install/migrate',
            'old_config_file': 'universe_wsgi.ini',
            'config_prefix': 'install_',
            'default_sqlite_file': './database/install.sqlite',
        },
}


def require_dialect_egg( db_url ):
    dialect = ( db_url.split( ':', 1 ) )[0]
    try:
        egg = dialect_to_egg[dialect]
        try:
            pkg_resources.require( egg )
            log.debug( "%s egg successfully loaded for %s dialect" % ( egg, dialect ) )
        except:
            # If the module is in the path elsewhere (i.e. non-egg), it'll still load.
            log.warning( "%s egg not found, but an attempt will be made to use %s anyway" % ( egg, dialect ) )
    except KeyError:
        # Let this go, it could possibly work with db's we don't support
        log.error( "database_connection contains an unknown SQLAlchemy database dialect: %s" % dialect )


def read_config_file_arg( argv, default, old_default ):
    if '-c' in argv:
        pos = argv.index( '-c' )
        argv.pop(pos)
        config_file = argv.pop( pos )
    else:
        if not os.path.exists( default ) and os.path.exists( old_default ):
            config_file = old_default
        else:
            config_file = default
    return config_file


def get_config( argv, cwd=None ):
    """
    Read sys.argv and parse out repository of migrations and database url.

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

    config_file = read_config_file_arg( argv, database_defaults.get( 'config_file', DEFAULT_CONFIG_FILE ), database_defaults.get( 'old_config_file' ) )
    repo = database_defaults[ 'repo' ]
    config_prefix = database_defaults.get( 'config_prefix', DEFAULT_CONFIG_PREFIX )
    default_sqlite_file = database_defaults[ 'default_sqlite_file' ]
    if cwd:
        config_file = os.path.join( cwd, config_file )

    cp = SafeConfigParser()
    cp.read( config_file )

    if cp.has_option( "app:main", "%sdatabase_connection" % config_prefix):
        db_url = cp.get( "app:main", "%sdatabase_connection" % config_prefix )
    elif cp.has_option( "app:main", "%sdatabase_file" % config_prefix ):
        db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % cp.get( "app:main", "database_file" )
    else:
        db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % default_sqlite_file

    require_dialect_egg( db_url )
    return dict(db_url=db_url, repo=repo, config_file=config_file, database=database)
