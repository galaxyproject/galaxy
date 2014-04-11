"""
API operations on library folders
"""
import os, string, shutil, urllib, re, socket, traceback
from galaxy import datatypes, jobs, web, security
from galaxy import exceptions
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.web.base.controller import BaseAPIController,UsesLibraryMixin,UsesLibraryMixinItems
# from galaxy.util.sanitize_html import sanitize_html

# from cgi import escape, FieldStorage
# from paste.httpexceptions import HTTPBadRequest

import logging
log = logging.getLogger( __name__ )

class FoldersController( BaseAPIController, UsesLibraryMixin, UsesLibraryMixinItems ):

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/folders/
        This would normally display a list of folders. However, that would
        be across multiple libraries, so it's not implemented.
        """
        raise exceptions.NotImplemented( 'Listing all accessible library folders is not implemented.' )

    @web.expose_api
    def show( self, trans, id, **kwd ):
        """
        show( self, trans, id, **kwd )
        *GET /api/folders/{encoded_folder_id}

        Displays information about a folder.

        :param  encoded_parent_folder_id:      the parent folder's id (required)
        :type   encoded_parent_folder_id:      an encoded id string (should be prefixed by 'F')  
        """
        # Eliminate any 'F' in front of the folder id. Just take the
        # last 16 characters:
        if ( len( id ) >= 17 ):
            id = id[-16:]
        # Retrieve the folder and return its contents encoded. Note that the
        # check_ownership=false since we are only displaying it.
        content = self.get_library_folder( trans, id, check_ownership=False,
                                           check_accessible=True )
        return self.encode_all_ids( trans, content.to_dict( view='element' ) )

    @web.expose_api
    def create( self, trans, encoded_parent_folder_id, **kwd ):

        """
        create( self, trans, encoded_parent_folder_id, **kwd )
        *POST /api/folders/{encoded_parent_folder_id}

        Create a new folder object underneath the one specified in the parameters.
        
        :param  encoded_parent_folder_id:      the parent folder's id (required)
        :type   encoded_parent_folder_id:      an encoded id string (should be prefixed by 'F')      

        :param  name:                          the name of the new folder (required)
        :type   name:                          str      
        
        :param  description:                   the description of the new folder
        :type   description:                   str

        :returns:   information about newly created folder, notably including ID
        :rtype:     dictionary

        :raises: RequestParameterMissingException, MalformedId, InternalServerError
        """

        payload = kwd.get( 'payload', None )
        if payload == None:
            raise exceptions.RequestParameterMissingException( "Missing required parameters 'encoded_parent_folder_id' and 'name'." )
        name = payload.get( 'name', None )
        description = payload.get( 'description', '' )
        if encoded_parent_folder_id == None:
            raise exceptions.RequestParameterMissingException( "Missing required parameter 'encoded_parent_folder_id'." )
        elif name == None:
            raise exceptions.RequestParameterMissingException( "Missing required parameter 'name'." )

        # encoded_parent_folder_id may be prefixed by 'F'
        encoded_parent_folder_id = self.__cut_the_prefix( encoded_parent_folder_id )
        
        try:
            decoded_parent_folder_id = trans.security.decode_id( encoded_parent_folder_id )
        except ValueError:
            raise exceptions.MalformedId( "Malformed folder id ( %s ) specified, unable to decode" % ( str( id ) ) )

        # TODO: refactor the functionality for use here instead of calling another controller
        params = dict( [ ( "name", name ), ( "description", description ) ] )
        status, output = trans.webapp.controllers['library_common'].create_folder( trans, 'api', encoded_parent_folder_id, '', **params )

        if 200 == status and len( output.items() ) == 1:
            for k, v in output.items():
                try:
                    folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( v.id )
                except Exception, e:
                    raise exceptions.InternalServerError( 'Error loading from the database.'  + str( e ))
                if folder:
                    return_dict = folder.to_dict( view='element' )
                    return_dict[ 'parent_library_id' ] = trans.security.encode_id( return_dict[ 'parent_library_id' ] )
                    return_dict[ 'parent_id' ] = 'F' + trans.security.encode_id( return_dict[ 'parent_id' ] )
                    return_dict[ 'id' ] = 'F' + trans.security.encode_id( return_dict[ 'id' ] )
                    return return_dict
        else:
            raise exceptions.InternalServerError( 'Error while creating a folder.'  + str(e))

    @web.expose_api
    def update( self, trans, id,  library_id, payload, **kwd ):
        """
        PUT /api/folders/{encoded_folder_id}
        For now this does nothing. There are no semantics for folders that
        indicates that an update operation is needed; the existing
        library_contents folder does not allow for update, either.
        """
        pass

    def __cut_the_prefix(self, encoded_id):
        if ( len( encoded_id ) == 17 and encoded_id.startswith( 'F' ) ):
            return encoded_id[-16:]
        else:
            return encoded_id

