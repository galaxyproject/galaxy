import sys, os.path, logging

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs

import pkg_resources
pkg_resources.require( "sqlalchemy-migrate" )

from migrate.versioning.shell import main
from ConfigParser import SafeConfigParser

log = logging.getLogger( __name__ )

config_file = 'universe_wsgi.ini'
if '-c' in sys.argv:
    pos = sys.argv.index( '-c' )
    sys.argv.pop( pos )
    config_file = sys.argv.pop( pos )
if not os.path.exists( config_file ):
    print "Galaxy config file does not exist (hint: use '-c config.ini' for non-standard locations): %s" % config_file
    sys.exit( 1 )
repo = 'lib/galaxy/tool_shed/migrate'

cp = SafeConfigParser()
cp.read( config_file )

if config_file == 'universe_wsgi.ini.sample' and 'GALAXY_TEST_DBURI' in os.environ:
    # Running functional tests.
    db_url = os.environ[ 'GALAXY_TEST_DBURI' ]
elif cp.has_option( "app:main", "database_connection" ):
    db_url = cp.get( "app:main", "database_connection" )
elif cp.has_option( "app:main", "database_file" ):
    db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % cp.get( "app:main", "database_file" )
else:
    db_url = "sqlite:///./database/universe.sqlite?isolation_level=IMMEDIATE"

dialect_to_egg = {
    "sqlite" : "pysqlite>=2",
    "postgres" : "psycopg2",
    "mysql" : "MySQL_python"
}
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

main( repository=repo, url=db_url )
