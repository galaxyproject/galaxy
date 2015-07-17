import os
import argparse
import ConfigParser
import sys
new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] )
sys.path = new_path

from galaxy import eggs
eggs.require('SQLAlchemy')
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker

import galaxy.model.tool_shed_install.mapping as mapping


def main( opts, session, model ):
    '''
    Find all tool shed repositories with the bad path and update with the correct path.
    '''
    for row in session.query( model.ToolShedRepository ).all():
        if 'shed_config_filename' in row.metadata:
            if row.metadata['shed_config_filename'] == opts.bad_filename:
                row.metadata['shed_config_filename'] = opts.good_filename
                session.add( row )
                session.flush()
    return 0


def create_database( config_file ):
    parser = ConfigParser.SafeConfigParser()
    parser.read( config_file )
    # Determine which database connection to use.
    database_connection = parser.get( 'app:main', 'install_database_connection' )
    if database_connection is None:
        database_connection = parser.get( 'app:main', 'database_connection' )
    if database_connection is None:
        database_connection = 'sqlite:///%s' % parser.get( 'app:main', 'database_file' )
    if database_connection is None:
        print 'Unable to determine correct database connection.'
        exit(1)

    '''Initialize the database file.'''
    dialect_to_egg = {
        "sqlite" : "pysqlite>=2",
        "postgres" : "psycopg2",
        "postgresql" : "psycopg2",
        "mysql" : "MySQL_python"
    }
    dialect = ( database_connection.split( ':', 1 ) )[0]
    try:
        egg = dialect_to_egg[ dialect ]
        try:
            eggs.require( egg )
            print( "%s egg successfully loaded for %s dialect" % ( egg, dialect ) )
        except:
            # If the module is in the path elsewhere (i.e. non-egg), it'll still load.
            print( "%s egg not found, but an attempt will be made to use %s anyway" % ( egg, dialect ) )
    except KeyError:
        # Let this go, it could possibly work with db's we don't support.
        print( "database_connection contains an unknown SQLAlchemy database dialect: %s" % dialect )

    # Initialize the database connection.
    engine = create_engine( database_connection )
    MetaData( bind=engine )
    install_session = scoped_session( sessionmaker( bind=engine, autoflush=False, autocommit=True ) )
    model = mapping.init( database_connection )
    return install_session, model

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument( '--config_file', dest='config_file', required=True, help="The path to your Galaxy configuration .ini file." )
    parser.add_argument( '--from', dest='bad_filename', required=True, help="The old, invalid path to the shed_tool_conf.xml or migrated_tools_conf.xml file." )
    parser.add_argument( '--to', dest='good_filename', required=True, help="The updated path to the shed_tool_conf.xml or migrated_tools_conf.xml file." )
    parser.add_argument( '--force', dest='force', action='store_true', help="Use this flag to set the new path even if the file does not (yet) exist there." )
    opts = parser.parse_args()
    if not os.path.exists( opts.good_filename ) and not opts.force:
        print 'The file %s does not exist, use the --force option to proceed.' % opts.good_filename
        exit(1)
    session, model = create_database( opts.config_file )
    exit( main( opts, session, model ) )
