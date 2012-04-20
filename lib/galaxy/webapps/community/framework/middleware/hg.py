"""
Middleware for handling hg authentication for users pushing change sets to local repositories.
"""
import os, logging
from sqlalchemy import *
from paste.auth.basic import AuthBasicAuthenticator
from paste.httpheaders import REMOTE_USER, AUTH_TYPE

from galaxy.webapps.community import model
from galaxy.util.hash_util import new_secure_hash

log = logging.getLogger(__name__)

class Hg( object ):
    def __init__( self, app, config ):
        self.app = app
        self.config = config
        # Authenticate this mercurial request using basic authentication
        self.authentication = AuthBasicAuthenticator( '', self.__basic_authentication )
        self.remote_address = None
        self.repository = None
        self.username = None
        self.action = None
    def __call__( self, environ, start_response ):
        cmd = self.__get_hg_command( **environ )
        if cmd == 'changegroup':
            # This is an hg clone from the command line.  When doing this, the following 5 commands, in order,
            # will be retrieved from environ: 
            # between -> heads -> changegroup -> capabilities -> listkeys
            #
            # Increment the value of the times_downloaded column in the repository table for the cloned repository.
            if 'PATH_INFO' in environ:
                path_info = environ[ 'PATH_INFO' ].lstrip( '/' )
                # An example of path_info is: '/repos/test/column1'
                path_info_components = path_info.split( '/' )
                username = path_info_components[1]
                name = path_info_components[2]
                # Instantiate a database connection
                db_url = self.config[ 'database_connection' ]
                engine = create_engine( db_url )
                connection = engine.connect()
                result_set = connection.execute( "select id from galaxy_user where username = '%s'" % username.lower() )
                for row in result_set:
                    # Should only be 1 row...
                    user_id = row[ 'id' ]
                result_set = connection.execute( "select times_downloaded from repository where user_id = %d and name = '%s'" % ( user_id, name.lower() ) )
                for row in result_set:
                    # Should only be 1 row...
                    times_downloaded = row[ 'times_downloaded' ]
                times_downloaded += 1
                connection.execute( "update repository set times_downloaded = %d where user_id = %d and name = '%s'" % ( times_downloaded, user_id, name.lower() ) )
                connection.close()
        if cmd == 'unbundle':
            # This is an hg push from the command line.  When doing this, the following 7 commands, in order,
            # will be retrieved from environ: 
            # between -> capabilities -> heads -> branchmap -> unbundle -> unbundle -> listkeys
            #
            # The mercurial API unbundle() ( i.e., hg push ) method ultimately requires authorization.
            # We'll force password entry every time a change set is pushed.
            #
            # When a user executes hg commit, it is not guaranteed to succeed.  Mercurial records your name 
            # and address with each change that you commit, so that you and others will later be able to 
            # tell who made each change. Mercurial tries to automatically figure out a sensible username 
            # to commit the change with. It will attempt each of the following methods, in order:
            #
            # 1) If you specify a -u option to the hg commit command on the command line, followed by a username, 
            # this is always given the highest precedence.
            # 2) If you have set the HGUSER environment variable, this is checked next.
            # 3) If you create a file in your home directory called .hgrc with a username entry, that 
            # will be used next.
            # 4) If you have set the EMAIL environment variable, this will be used next.
            # 5) Mercurial will query your system to find out your local user name and host name, and construct 
            # a username from these components. Since this often results in a username that is not very useful, 
            # it will print a warning if it has to do this.
            #
            # If all of these mechanisms fail, Mercurial will fail, printing an error message. In this case, it 
            # will not let you commit until you set up a username.
            result = self.authentication( environ )
            if isinstance( result, str ):
                # Authentication was successful
                AUTH_TYPE.update( environ, 'basic' )
                REMOTE_USER.update( environ, result )
            else:
                return result.wsgi_application( environ, start_response )
        return self.app( environ, start_response )
    def __get_hg_command( self, **kwd ):
        # Pulls mercurial commands from environ[ 'QUERY_STRING" ] and returns them.
        if 'QUERY_STRING' in kwd:
            for qry in kwd[ 'QUERY_STRING' ].split( '&' ):
                if qry.startswith( 'cmd' ):
                    return qry.split( '=' )[ -1 ]
        return None
    def __basic_authentication( self, environ, username, password ):
        # The environ parameter is needed in basic authentication.
        return self.__authenticate( username, password )
    def __authenticate( self, username, password ):
        # Instantiate a database connection
        db_url = self.config[ 'database_connection' ]
        engine = create_engine( db_url )
        connection = engine.connect()
        result_set = connection.execute( "select email, password from galaxy_user where username = '%s'" % username.lower() )
        for row in result_set:
            # Should only be 1 row...
            db_email = row[ 'email' ]
            db_password = row[ 'password' ]
        connection.close()
        # Check if password matches db_password when hashed.
        return new_secure_hash( text_type=password ) == db_password
