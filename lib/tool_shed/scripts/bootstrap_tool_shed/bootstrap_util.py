#!/usr/bin/python
import argparse
import ConfigParser
import os
import sys

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] )
sys.path = new_path

from galaxy import eggs
eggs.require( "SQLAlchemy >= 0.4" )
import galaxy.webapps.tool_shed.model.mapping as tool_shed_model
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.exc import OperationalError

from tool_shed.util import xml_util

def check_db( config_parser ):
    dburi = None
    
    if config_parser.has_option( 'app:main', 'database_connection' ):
        dburi = config_parser.get( 'app:main', 'database_connection' )
    elif config_parser.has_option( 'app:main', 'database_file' ):
        db_file = config_parser.get( 'app:main', 'database_file' )
        dburi = "sqlite:///%s?isolation_level=IMMEDIATE" % db_file
    else:
        print 'The database configuration setting is missing from the tool_shed.ini file.  Add this setting before attempting to bootstrap.'
        exit(1)
    
    sa_session = None

    database_exists_message = 'The database configured for this Tool Shed is not new, so bootstrapping is not allowed.  '
    database_exists_message += 'Create a new database that has not been migrated before attempting to bootstrap.'
   
    try:
        model = tool_shed_model.init( config_parser.get( 'app:main', 'file_path' ), dburi, engine_options={}, create_tables=False )
        sa_session = model.context.current
        print database_exists_message
        exit(1)
    except ProgrammingError, e:
        pass
    except OperationalError, e:
        pass
    
    try:
        if sa_session is not None:
            result = sa_session.execute( 'SELECT version FROM migrate_version' ).first()
            if result[0] >= 2:
                print database_exists_message
                exit(1)
            else:
                pass
    except ProgrammingError, e:
        pass
    
    if config_parser.has_option( 'app:main', 'hgweb_config_dir' ):
        hgweb_config_parser = ConfigParser.ConfigParser()
        hgweb_dir = config_parser.get( 'app:main', 'hgweb_config_dir' )
        hgweb_config_file = os.path.join( hgweb_dir, 'hgweb.config' )
        if not os.path.exists( hgweb_config_file ):
            exit(0)
        hgweb_config_parser.read( hgweb_config_file )
        configured_repos = hgweb_config_parser.items( 'paths' )
        if len( configured_repos ) >= 1:
            message = "This Tool Shed's hgweb.config file contains entries, so bootstrapping is not allowed.  Delete"
            message += " the current hgweb.config file along with all associated repositories in the configured "
            message += "location before attempting to boostrap."
            print 
            exit(1)
        else:
            exit(0)
    else:
        exit(0)
    
    exit(0)
    
def admin_user_info( config_parser ):
    user_info_config = os.path.abspath( os.path.join( os.getcwd(), 'lib/tool_shed/scripts/bootstrap_tool_shed', 'user_info.xml' ) )
    tree, error_message = xml_util.parse_xml( user_info_config )
    if tree is None:
        print "The XML file ", user_info_config, " seems to be invalid, using defaults."
        email = 'admin@test.org'
        password = 'testuser'
        username = 'admin'
    else:
        root = tree.getroot()
        for elem in root:
            if elem.tag == 'email':
                email = elem.text
            elif elem.tag == 'password':
                password = elem.text
            elif elem.tag == 'username':
                username = elem.text
    print '%s__SEP__%s__SEP__%s' % ( username, email, password )
    return 0

def get_local_tool_shed_url( config_parser ):
    port = '9009'
    if config_parser.has_section( 'server:main' ):
        if config_parser.has_option( 'server:main', 'port' ):
            port = config_parser.get( 'server:main', 'port' )
    host = '127.0.0.1'
    print 'http://%s:%s' % ( host, port )
    return 0

def main( args ):
    config_parser = ConfigParser.ConfigParser()
    
    if os.path.exists( args.config ):
        config_parser.read( args.config )
    else:
        return 1

    if args.method == 'check_db':
        return check_db( config_parser )
    elif args.method == 'admin_user_info':
        return admin_user_info( config_parser )
    elif args.method == 'get_url':
        return get_local_tool_shed_url( config_parser )
    else:
        return 1
    
parser = argparse.ArgumentParser()
parser.add_argument( '-c', '--config_file', dest='config', action='store', default='config/tool_shed.ini.sample' )
parser.add_argument( '-e', '--execute', dest='method', action='store', default='check_db' )
args = parser.parse_args()

if __name__ == '__main__':
    exit( main( args ) )
