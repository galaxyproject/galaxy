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

cp = SafeConfigParser()
cp.read( "universe_wsgi.ini" )

if cp.has_option( "app:main", "database_connection" ):
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

main( repository='lib/galaxy/model/migrate', url=db_url )
