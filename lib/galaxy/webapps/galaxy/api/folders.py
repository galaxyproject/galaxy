"""
API operations on folders 
"""
import logging, os, string, shutil, urllib, re, socket, traceback
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.orm import *

log = logging.getLogger( __name__ )

class FoldersController( BaseAPIController, UsesLibraryMixin, UsesLibraryMixinItems ):

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/folders/
        This would normally display a list of folders. However, that would
        be across multiple libraries, so it's not implemented yet.
        """
        pass

    @web.expose_api
    def show( self, trans, id, **kwd ):
        """
        GET /api/folders/{encoded_folder_id}
        Displays information about a folder 
        """
        # Eliminate any 'F' in front of the folder id. Just take the
        # last 16 characters:
        if ( len( id ) >= 17 ):
            id = id[-16:]
        # Retrieve the folder and return its contents encoded. Note that the
        # check_ownership=false since we are only displaying it.
        content = self.get_library_folder( trans, id, check_ownership=False, 
                                           check_accessible=True )
        return self.encode_all_ids( trans, content.get_api_value( view='element' ) )

    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/folders/{encoded_folder_id}
        Create a new object underneath the one specified in the parameters.
        This will use the same parameters and semantics as 
        /api/libraries/{LibID}/contents/{ContentId} for consistency.
        This means that datasets and folders can be generated. Note that
        /api/libraries/{LibID}/contents/{ContentId} did not need the library
        id to function properly, which is why this functionality has been
        moved here.

        o payload's relevant params:
          - folder_id: This is the parent folder's id (required)
        """
        log.debug( "FoldersController.create: enter" )
        # TODO: Create a single point of exit if possible. For now we only
        # exit at the end and on exceptions.
        if 'folder_id' not in payload:
            trans.response.status = 400
            return "Missing requred 'folder_id' parameter."
        else:
            folder_id = payload.pop( 'folder_id' )
            class_name, folder_id = self.__decode_library_content_id( trans, folder_id )

        try:
            # security is checked in the downstream controller
            parent_folder = self.get_library_folder( trans, folder_id, check_ownership=False, check_accessible=False )
        except Exception, e:
            return str( e )

        real_parent_folder_id = trans.security.encode_id( parent_folder.id )

        # Note that this will only create a folder; the library_contents will
        # also allow files to be generated, though that encompasses generic
        # contents:
        # TODO: reference or change create_folder, which points to the
        # library browsing; we just want to point to the /api/folders URI.
        status, output = trans.webapp.controllers['library_common'].create_folder( trans, 'api', real_parent_folder_id, '', **payload )
        rval = []

        # SM: When a folder is sucessfully created:
        #   - get all of the created folders. We know that they're
        #     folders, so prepend an "F" to them.
        if 200 == status:
            for k, v in output.items():
                if type( v ) == trans.app.model.LibraryDatasetDatasetAssociation:
                    v = v.library_dataset
                encoded_id = 'F' + trans.security.encode_id( v.id )
                rval.append( dict( id = encoded_id,
                                   name = v.name,
                                   url = url_for( 'folder', id=encoded_id ) ) )
        else: 
            log.debug( "Error creating folder; setting output and status" )
            trans.response.status = status
            rval = output 
        return rval 

    @web.expose_api
    def update( self, trans, id,  library_id, payload, **kwd ):
        """
        PUT /api/folders/{encoded_folder_id}
        For now this does nothing. There are no semantics for folders that
        indicates that an update operation is needed; the existing 
        library_contents folder does not allow for update, either.
        """
        pass

    # TODO: Move this to library_common. This doesn't really belong in any
    # of the other base controllers.
    def __decode_library_content_id( self, trans, content_id ):
        if ( len( content_id ) % 16 == 0 ):
            return 'LibraryDataset', content_id
        elif ( content_id.startswith( 'F' ) ):
            return 'LibraryFolder', content_id[1:]
        else:
            raise HTTPBadRequest( 'Malformed library content id ( %s ) specified, unable to decode.' % str( content_id ) )
