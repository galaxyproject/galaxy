#!/usr/bin/env python

import ConfigParser
import logging
import os
import re
import sys

from optparse import OptionParser

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] )
sys.path = new_path

from galaxy import eggs
eggs.require( "SQLAlchemy >= 0.4" )
eggs.require( 'mercurial' )

from galaxy.web import security
import galaxy.webapps.tool_shed.config as tool_shed_config
from galaxy.webapps.tool_shed.model import mapping
from tool_shed.util import xml_util

log = logging.getLogger( __name__ )


VALID_PUBLICNAME_RE = re.compile( "^[a-z0-9\-]+$" )
VALID_EMAIL_RE = re.compile( "[^@]+@[^@]+\.[^@]+" )


class BootstrapApplication( object ):
    """
    Creates a basic Tool Shed application in order to discover the database connection and use SQL
    to create a user and API key.
    """

    def __init__( self, config ):
        self.config = config
        if not self.config.database_connection:
            self.config.database_connection = "sqlite:///%s?isolation_level=IMMEDIATE" % str( config.database )
        print 'Using database connection: ', self.config.database_connection
        # Setup the database engine and ORM
        self.model = mapping.init( self.config.file_path,
                                   self.config.database_connection,
                                   engine_options={},
                                   create_tables=False )
        self.security = security.SecurityHelper( id_secret=self.config.id_secret )
        self.hgweb_config_manager = self.model.hgweb_config_manager
        self.hgweb_config_manager.hgweb_config_dir = self.config.hgweb_config_dir
        print 'Using hgweb.config file: ', self.hgweb_config_manager.hgweb_config

    @property
    def sa_session( self ):
        """Returns a SQLAlchemy session."""
        return self.model.context.current

    def shutdown( self ):
        pass

def create_api_key( app, user ):
    api_key = app.security.get_new_guid()
    new_key = app.model.APIKeys()
    new_key.user_id = user.id
    new_key.key = api_key
    app.sa_session.add( new_key )
    app.sa_session.flush()
    return api_key
    
def create_user( app ):
    user_info_config = os.path.abspath( os.path.join( app.config.root, 'lib/tool_shed/scripts/bootstrap_tool_shed', 'user_info.xml' ) )
    email = None
    password = None
    username = None
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
    if email and password and username:
        invalid_message = validate( email, password, username )
        if invalid_message:
            print invalid_message
        else:
            user = app.model.User( email=email )
            user.set_password_cleartext( password )
            user.username = username
            app.sa_session.add( user )
            app.sa_session.flush()
            app.model.security_agent.create_private_user_role( user )
            return user
    else:
        print "Missing required values for email: ", email, ", password: ", password, ", username: ", username
    return None

def validate( email, password, username ):
    message = validate_email( email )
    if not message:
        message = validate_password( password )
    if not message:
        message = validate_publicname( username )
    return message

def validate_email( email ):
    """Validates the email format."""
    message = ''
    if not( VALID_EMAIL_RE.match( email ) ):
        message = "Please enter a real email address."
    elif len( email ) > 255:
        message = "Email address exceeds maximum allowable length."
    return message

def validate_password( password ):
    if len( password ) < 6:
        return "Use a password of at least 6 characters"
    return ''

def validate_publicname( username ):
    """Validates the public username."""
    if len( username ) < 3:
        return "Public name must be at least 3 characters in length"
    if len( username ) > 255:
        return "Public name cannot be more than 255 characters in length"
    if not( VALID_PUBLICNAME_RE.match( username ) ):
        return "Public name must contain only lower-case letters, numbers and '-'"
    return ''

if __name__ == "__main__":
    parser = OptionParser()
    ( options, args ) = parser.parse_args()
    try:
        ini_file = args[ 0 ]
    except IndexError:
        print "Usage: python %s <tool shed .ini file> [options]" % sys.argv[ 0 ]
        exit( 127 )
    config_parser = ConfigParser.ConfigParser( { 'here':os.getcwd() } )
    print "Reading ini file: ", ini_file
    config_parser.read( ini_file )
    config_dict = {}
    for key, value in config_parser.items( "app:main" ):
        config_dict[ key ] = value
    config = tool_shed_config.Configuration( **config_dict )
    app = BootstrapApplication( config )
    user = create_user( app )
    if user is not None:
        api_key = create_api_key( app, user )
        print "Created new user with public username '", user.username, ".  An API key was also created and associated with the user."
        exit(0)
    else:
        print "Problem creating a new user and an associated API key."
        exit(1)
