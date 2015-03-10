import sys
import os.path
import logging

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] )  # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs

eggs.require( "SQLAlchemy" )
eggs.require( "decorator" )
eggs.require( "Tempita " )
eggs.require( "six" )  # Required by sqlalchemy-migrate
eggs.require( "sqlparse" )  # Required by sqlalchemy-migrate
eggs.require( "sqlalchemy-migrate" )

from migrate.versioning.shell import main
from ConfigParser import SafeConfigParser

from galaxy.model.orm.scripts import require_dialect_egg
from galaxy.model.orm.scripts import read_config_file_arg
from galaxy.util.properties import load_app_properties

log = logging.getLogger( __name__ )

config_file = read_config_file_arg( sys.argv, 'config/galaxy.ini', 'universe_wsgi.ini' )
if not os.path.exists( config_file ):
    print "Galaxy config file does not exist (hint: use '-c config.ini' for non-standard locations): %s" % config_file
    sys.exit( 1 )
repo = 'lib/tool_shed/galaxy_install/migrate'

properties = load_app_properties( ini_file=config_file )
cp = SafeConfigParser()
cp.read( config_file )

if config_file == 'config/galaxy.ini.sample' and 'GALAXY_TEST_DBURI' in os.environ:
    # Running functional tests.
    db_url = os.environ[ 'GALAXY_TEST_DBURI' ]
elif "install_database_connection" in properties:
    db_url = properties[ "install_database_connection" ]
elif "database_connection" in properties:
    db_url = properties[ "database_connection" ]
elif "database_file" in properties:
    db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % properties[ "database_file" ]
else:
    db_url = "sqlite:///./database/universe.sqlite?isolation_level=IMMEDIATE"

require_dialect_egg( db_url )

main( repository=repo, url=db_url )
