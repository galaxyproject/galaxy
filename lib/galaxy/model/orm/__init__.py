import pkg_resources
pkg_resources.require( "SQLAlchemy >= 0.4" )

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.interfaces import *

import logging
log = logging.getLogger( __name__ )


dialect_to_egg = {
    "sqlite": "pysqlite>=2",
    "postgres": "psycopg2",
    "postgresql": "psycopg2",
    "mysql": "MySQL_python"
}


def load_egg_for_url( url ):
    # Load the appropriate db module
    dialect = __guess_dialect_for_url( url )
    try:
        egg = dialect_to_egg[dialect]
        try:
            pkg_resources.require( egg )
            log.debug( "%s egg successfully loaded for %s dialect" % ( egg, dialect ) )
        except:
            # If the module's in the path elsewhere (i.e. non-egg), it'll still load.
            log.warning( "%s egg not found, but an attempt will be made to use %s anyway" % ( egg, dialect ) )
    except KeyError:
        # Let this go, it could possibly work with db's we don't support
        log.error( "database_connection contains an unknown SQLAlchemy database dialect: %s" % dialect )


def __guess_dialect_for_url( url ):
    return (url.split(':', 1))[0]
