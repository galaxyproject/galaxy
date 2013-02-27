# This script allows easy access to Galaxy's database layer via the
# Galaxy models. For example:
# % python -i scripts/db_shell.py
# >>> new_user = User("admin@gmail.com")
# >>> new_user.set_password
# >>> sa_session.add(new_user)
# >>> sa_session.commit()
# >>> sa_session.query(User).all()
# 
# You can also use this script as a library, for instance see https://gist.github.com/1979583
# TODO: This script overlaps a lot with manage_db.py and create_db.py,
# these should maybe be refactored to remove duplication.
import sys, os.path, logging

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs

import pkg_resources
pkg_resources.require( "sqlalchemy-migrate" )
pkg_resources.require( "SQLAlchemy" )

from ConfigParser import SafeConfigParser

log = logging.getLogger( __name__ )

if sys.argv[-1] in [ 'tool_shed' ]:
    # Need to pop the last arg so the command line args will be correct
    # for sqlalchemy-migrate 
    webapp = sys.argv.pop()
    config_file = 'community_wsgi.ini'
    repo = 'lib/galaxy/webapps/tool_shed/model/migrate'
else:
    # Poor man's optparse
    config_file = 'universe_wsgi.ini'
    if '-c' in sys.argv:
        pos = sys.argv.index( '-c' )
        sys.argv.pop(pos)
        config_file = sys.argv.pop( pos )
    if not os.path.exists( config_file ):
        print "Galaxy config file does not exist (hint: use '-c config.ini' for non-standard locations): %s" % config_file
        sys.exit( 1 )
    repo = 'lib/galaxy/model/migrate'

cp = SafeConfigParser()
cp.read( config_file )

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

# Setup DB scripting environment 
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import *

engine = create_engine(db_url, echo=True)
db_session = scoped_session( sessionmaker( bind = engine ) )
from galaxy.model.mapping import context as sa_session
sa_session.bind = engine
from galaxy.model import *

