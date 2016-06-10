import logging
import os.path
import sys
from ConfigParser import SafeConfigParser

from migrate.versioning.shell import main

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

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

main( repository=repo, url=db_url )
