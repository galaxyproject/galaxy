import sys
import os.path
import logging

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] )  # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs

import pkg_resources
pkg_resources.require( "SQLAlchemy" )
pkg_resources.require( "decorator" )
pkg_resources.require( "Tempita " )
pkg_resources.require( "sqlalchemy-migrate" )

from migrate.versioning.shell import main
from ConfigParser import SafeConfigParser

from galaxy.model.orm.scripts import require_dialect_egg
from galaxy.model.orm.scripts import read_config_file_arg

log = logging.getLogger( __name__ )

config_file = read_config_file_arg( sys.argv, 'config/galaxy.ini', 'universe_wsgi.ini' )
if not os.path.exists( config_file ):
    print "Galaxy config file does not exist (hint: use '-c config.ini' for non-standard locations): %s" % config_file
    sys.exit( 1 )
repo = 'lib/tool_shed/galaxy_install/migrate'

cp = SafeConfigParser()
cp.read( config_file )

if config_file == 'config/galaxy.ini.sample' and 'GALAXY_TEST_DBURI' in os.environ:
    # Running functional tests.
    db_url = os.environ[ 'GALAXY_TEST_DBURI' ]
elif cp.has_option( "app:main", "install_database_connection" ):
    db_url = cp.get( "app:main", "install_database_connection" )
elif cp.has_option( "app:main", "database_connection" ):
    db_url = cp.get( "app:main", "database_connection" )
elif cp.has_option( "app:main", "database_file" ):
    db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % cp.get( "app:main", "database_file" )
else:
    db_url = "sqlite:///./database/universe.sqlite?isolation_level=IMMEDIATE"

require_dialect_egg( db_url )

main( repository=repo, url=db_url )
