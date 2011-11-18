import sys, os.path, logging

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs
from galaxy.model.migrate.check import create_or_verify_database as create_db

import pkg_resources

from ConfigParser import SafeConfigParser

log = logging.getLogger( __name__ )

# Poor man's optparse
config_file = 'universe_wsgi.ini'
if '-c' in sys.argv:
    pos = sys.argv.index( '-c' )
    sys.argv.pop(pos)
    config_file = sys.argv.pop( pos )
if not os.path.exists( config_file ):
    print "Galaxy config file does not exist (hint: use '-c config.ini' for non-standard locations): %s" % config_file
    sys.exit( 1 )

cp = SafeConfigParser()
cp.read( config_file )

if cp.has_option( "app:main", "database_connection" ):
    db_url = cp.get( "app:main", "database_connection" )
elif cp.has_option( "app:main", "database_file" ):
    db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % cp.get( "app:main", "database_file" )
else:
    db_url = "sqlite:///./database/universe.sqlite?isolation_level=IMMEDIATE"

create_db(db_url, config_file)
