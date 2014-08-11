"""Middle-ware for handling hg authentication for users pushing change sets to local repositories."""
import json
import logging
import os
import sqlalchemy
import sys
import tempfile
from paste.auth.basic import AuthBasicAuthenticator
from paste.httpheaders import AUTH_TYPE
from paste.httpheaders import REMOTE_USER

from galaxy.util import asbool
from galaxy.util.hash_util import new_secure_hash
from tool_shed.util import hg_util
import tool_shed.repository_types.util as rt_util

from galaxy import eggs
eggs.require( 'mercurial' )
import mercurial.__version__

log = logging.getLogger(__name__)

CHUNK_SIZE = 65536


class Hg( object ):

    def __init__( self, app, config ):
        print "mercurial version is:", mercurial.__version__.version
        self.app = app
        self.config = config
        # Authenticate this mercurial request using basic authentication
        self.authentication = AuthBasicAuthenticator( 'hgweb in the tool shed', self.__basic_authentication )
        # Determine the database url
        if 'database_connection' in self.config:
            self.db_url = self.config[ 'database_connection' ]
        else:
            self.db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % self.config[ 'database_file' ]
        # Keep track of whether we're setting repository metadata so that we do not increment the times_downloaded
        # count for the repository.
        self.setting_repository_metadata = False

    def __call__( self, environ, start_response ):
        if 'PATH_INFO' in environ:
            path_info = environ[ 'PATH_INFO' ].lstrip( '/' )
            if path_info == 'repository/reset_all_metadata':
                self.setting_repository_metadata = True
        cmd = self.__get_hg_command( **environ )
        # The 'getbundle' command indicates that a mercurial client is getting a bundle of one or more changesets, indicating
        # a clone or a pull.  However, we do not want to increment the times_downloaded count if we're only setting repository
        # metadata.
        if cmd == 'getbundle' and not self.setting_repository_metadata:
            common, _ = environ[ 'HTTP_X_HGARG_1' ].split( '&' )
            # The 'common' parameter indicates the full sha-1 hash of the changeset the client currently has checked out. If
            # this is 0000000000000000000000000000000000000000, then the client is performing a fresh checkout. If it has any
            # other value, the client is getting updates to an existing checkout.
            if common == 'common=0000000000000000000000000000000000000000':
                # Increment the value of the times_downloaded column in the repository table for the cloned repository.
                if 'PATH_INFO' in environ:
                    # Instantiate a database connection
                    engine = sqlalchemy.create_engine( self.db_url )
                    connection = engine.connect()
                    path_info = environ[ 'PATH_INFO' ].lstrip( '/' )
                    user_id, repository_name = self.__get_user_id_repository_name_from_path_info( connection, path_info )
                    sql_cmd = "SELECT times_downloaded FROM repository WHERE user_id = %d AND name = '%s'" % \
                        ( user_id, repository_name.lower() )
                    result_set = connection.execute( sql_cmd )
                    for row in result_set:
                        # Should only be 1 row...
                        times_downloaded = row[ 'times_downloaded' ]
                    times_downloaded += 1
                    sql_cmd = "UPDATE repository SET times_downloaded = %d WHERE user_id = %d AND name = '%s'" % \
                        ( times_downloaded, user_id, repository_name.lower() )
                    connection.execute( sql_cmd )
                    connection.close()
        elif cmd in [ 'unbundle', 'pushkey' ]:
            # This is an hg push from the command line.  When doing this, the following commands, in order,
            # will be retrieved from environ (see the docs at http://mercurial.selenic.com/wiki/WireProtocol):
            # # If mercurial version >= '2.2.3': capabilities -> batch -> branchmap -> unbundle -> listkeys -> pushkey -> listkeys
            #
            # The mercurial API unbundle() ( i.e., hg push ) and pushkey() methods ultimately require authorization.
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
            if not isinstance( result, str ) and cmd == 'unbundle' and 'wsgi.input' in environ:
                bundle_data_stream = environ[ 'wsgi.input' ]
                # Convert the incoming mercurial bundle into a json object and persit it to a temporary file for inspection.
                fh = tempfile.NamedTemporaryFile( 'wb', prefix="tmp-hg-bundle"  )
                tmp_filename = fh.name
                fh.close()
                fh = open( tmp_filename, 'wb' )
                while 1:
                    chunk = bundle_data_stream.read( CHUNK_SIZE )
                    if not chunk:
                        break
                    fh.write( chunk )
                fh.close()
                fh = open( tmp_filename, 'rb' )
                changeset_groups = json.loads( hg_util.bundle_to_json( fh ) )
                fh.close()
                try:
                    os.unlink( tmp_filename )
                except:
                    pass
                if changeset_groups:
                    # Check the repository type to make sure inappropriate files are not being pushed.
                    if 'PATH_INFO' in environ:
                        # Instantiate a database connection
                        engine = sqlalchemy.create_engine( self.db_url )
                        connection = engine.connect()
                        path_info = environ[ 'PATH_INFO' ].lstrip( '/' )
                        user_id, repository_name = self.__get_user_id_repository_name_from_path_info( connection, path_info )
                        sql_cmd = "SELECT type FROM repository WHERE user_id = %d AND name = '%s'" % ( user_id, repository_name.lower() )
                        result_set = connection.execute( sql_cmd )
                        for row in result_set:
                            # Should only be 1 row...
                            repository_type = str( row[ 'type' ] )
                        if repository_type == rt_util.REPOSITORY_SUITE_DEFINITION:
                            # Handle repositories of type repository_suite_definition, which can only contain a single
                            # file named repository_dependencies.xml.
                            for entry in changeset_groups:
                                if len( entry ) == 2:
                                    # We possibly found an altered file entry.
                                    filename, change_list = entry
                                    if filename and isinstance( filename, str ):
                                        if filename == rt_util.REPOSITORY_DEPENDENCY_DEFINITION_FILENAME:
                                            # Make sure the any complex repository dependency definitions contain valid <repository> tags.
                                            is_valid, error_msg = self.repository_tags_are_valid( filename, change_list )
                                            if not is_valid:
                                                log.debug( error_msg )
                                                return self.__display_exception_remotely( start_response, error_msg )
                                        else:
                                            msg = "Only a single file named repository_dependencies.xml can be pushed to a repository "
                                            msg += "of type 'Repository suite definition'."
                                            log.debug( msg )
                                            return self.__display_exception_remotely( start_response, msg )
                        elif repository_type == rt_util.TOOL_DEPENDENCY_DEFINITION:
                            # Handle repositories of type tool_dependency_definition, which can only contain a single
                            # file named tool_dependencies.xml.
                            for entry in changeset_groups:
                                if len( entry ) == 2:
                                    # We possibly found an altered file entry.
                                    filename, change_list = entry
                                    if filename and isinstance( filename, str ):
                                        if filename == rt_util.TOOL_DEPENDENCY_DEFINITION_FILENAME:
                                            # Make sure the any complex repository dependency definitions contain valid <repository> tags.
                                            is_valid, error_msg = self.repository_tags_are_valid( filename, change_list )
                                            if not is_valid:
                                                log.debug( error_msg )
                                                return self.__display_exception_remotely( start_response, error_msg )
                                        else:
                                            msg = "Only a single file named tool_dependencies.xml can be pushed to a repository "
                                            msg += "of type 'Tool dependency definition'."
                                            log.debug( msg )
                                            return self.__display_exception_remotely( start_response, msg )
                        else:
                            # If the changeset includes changes to dependency definition files, make sure tag sets
                            # are not missing "toolshed" or "changeset_revision" attributes since automatically populating
                            # them is not supported when pushing from the command line.  These attributes are automatically
                            # populated only when using the tool shed upload utility.
                            for entry in changeset_groups:
                                if len( entry ) == 2:
                                    # We possibly found an altered file entry.
                                    filename, change_list = entry
                                    if filename and isinstance( filename, str ):
                                        if filename in [ rt_util.REPOSITORY_DEPENDENCY_DEFINITION_FILENAME,
                                                         rt_util.TOOL_DEPENDENCY_DEFINITION_FILENAME ]:
                                            # We check both files since tool dependency definitions files can contain complex
                                            # repository dependency definitions.
                                            is_valid, error_msg = self.repository_tags_are_valid( filename, change_list )
                                            if not is_valid:
                                                log.debug( error_msg )
                                                return self.__display_exception_remotely( start_response, error_msg )
            if isinstance( result, str ):
                # Authentication was successful
                AUTH_TYPE.update( environ, 'basic' )
                REMOTE_USER.update( environ, result )
            else:
                return result.wsgi_application( environ, start_response )
        return self.app( environ, start_response )

    def __authenticate( self, username, password ):
        db_password = None
        # Instantiate a database connection
        engine = sqlalchemy.create_engine( self.db_url )
        connection = engine.connect()
        result_set = connection.execute( "select email, password from galaxy_user where username = '%s'" % username.lower() )
        for row in result_set:
            # Should only be 1 row...
            db_email = row[ 'email' ]
            db_password = row[ 'password' ]
        connection.close()
        if db_password:
            # Check if password matches db_password when hashed.
            return new_secure_hash( text_type=password ) == db_password
        return False

    def __authenticate_remote_user( self, environ, username, password ):
        """
        Look after a remote user and "authenticate" - upstream server should already have achieved
        this for us, but we check that the user exists at least. Hg allow_push = must include username
        - some versions of mercurial blow up with 500 errors.
        """
        db_username = None
        ru_email = environ[ 'HTTP_REMOTE_USER' ].lower()
        ## Instantiate a database connection...
        engine = sqlalchemy.create_engine( self.db_url )
        connection = engine.connect()
        result_set = connection.execute( "select email, username, password from galaxy_user where email = '%s'" % ru_email )
        for row in result_set:
            # Should only be 1 row...
            db_email = row[ 'email' ]
            db_password = row[ 'password' ]
            db_username = row[ 'username' ]
        connection.close()
        if db_username:
            # We could check the password here except that the function galaxy.web.framework.get_or_create_remote_user()
            # does some random generation of a password - so that no-one knows the password and only the hash is stored...
            return db_username == username
        return False

    def __basic_authentication( self, environ, username, password ):
        """The environ parameter is needed in basic authentication.  We also check it if use_remote_user is true."""
        if asbool( self.config.get( 'use_remote_user', False ) ):
            assert "HTTP_REMOTE_USER" in environ, "use_remote_user is set but no HTTP_REMOTE_USER variable"
            return self.__authenticate_remote_user( environ, username, password )
        else:
            return self.__authenticate( username, password )

    def __display_exception_remotely( self, start_response, msg ):
        # Display the exception to the remote user's command line.
        status = "500 %s" % msg
        response_headers = [ ("content-type", "text/plain") ]
        start_response( status, response_headers, sys.exc_info() )
        return [ msg ]

    def __get_hg_command( self, **kwd ):
        """Pulls mercurial commands from environ[ 'QUERY_STRING" ] and returns them."""
        if 'QUERY_STRING' in kwd:
            for qry in kwd[ 'QUERY_STRING' ].split( '&' ):
                if qry.startswith( 'cmd' ):
                    return qry.split( '=' )[ -1 ]
        return None

    def __get_user_id_repository_name_from_path_info( self, db_connection, path_info ):
        # An example of path_info is: '/repos/test/column1'
        path_info_components = path_info.split( '/' )
        username = path_info_components[ 1 ]
        repository_name = path_info_components[ 2 ]
        # Get the id of the current user using hg from the command line.
        result_set = db_connection.execute( "select id from galaxy_user where username = '%s'" % username.lower() )
        for row in result_set:
            # Should only be 1 row...
            user_id = row[ 'id' ]
        return user_id, repository_name

    def repository_tag_is_valid( self, filename, line ):
        """
        Checks changes made to <repository> tags in a dependency definition file being pushed to the
        Tool Shed from the command line to ensure that all required attributes exist.
        """
        required_attributes = [ 'toolshed', 'name', 'owner', 'changeset_revision' ]
        defined_attributes = line.split()
        for required_attribute in required_attributes:
            defined = False
            for defined_attribute in defined_attributes:
                if defined_attribute.startswith( required_attribute ):
                    defined = True
                    break
            if not defined:
                error_msg = 'The %s file contains a <repository> tag that is missing the required attribute %s.  ' % \
                    ( filename, required_attribute )
                error_msg += 'Automatically populating dependency definition attributes occurs only when using '
                error_msg += 'the Tool Shed upload utility.  '
                return False, error_msg
        return True, ''
    
    def repository_tags_are_valid( self, filename, change_list ):
        """
        Make sure the any complex repository dependency definitions contain valid <repository> tags when pushing
        changes to the tool shed on the command line.
        """
        tag = '<repository'
        for change_dict in change_list:
            lines = get_change_lines_in_file_for_tag( tag, change_dict )
            for line in lines:
                is_valid, error_msg = repository_tag_is_valid( filename, line )
                if not is_valid:
                    return False, error_msg
        return True, ''
