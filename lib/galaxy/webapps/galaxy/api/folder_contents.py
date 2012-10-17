"""
API operations on the contents of a library.
"""
import logging, os, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.orm import *

log = logging.getLogger( __name__ )

class FolderContentsController( BaseAPIController, UsesLibraryMixin, UsesLibraryMixinItems ):

    @web.expose_api
    def index( self, trans, folder_id, **kwd ):
        """
        GET /api/folders/{encoded_folder_id}/contents
        Displays a collection (list) of a folder's contents (files and folders).
        The /api/library_contents/{encoded_library_id}/contents
        lists everything in a library recursively, which is not what
        we want here. We could add a parameter to use the recursive
        style, but this is meant to act similar to an "ls" directory listing.
        """
        rval = []
        current_user_roles = trans.get_current_user_roles()

        def traverse( folder ):
            admin = trans.user_is_admin()
            rval = []
            for subfolder in folder.active_folders:
                if not admin:
                    can_access, folder_ids = trans.app.security_agent.check_folder_contents( trans.user, current_user_roles, subfolder )
                if (admin or can_access) and not subfolder.deleted:
                    subfolder.api_type = 'folder'
                    rval.append( subfolder )
            for ld in folder.datasets:
                if not admin:
                    can_access = trans.app.security_agent.can_access_dataset( current_user_roles, ld.library_dataset_dataset_association.dataset )
                if (admin or can_access) and not ld.deleted:
                    ld.api_type = 'file'
                    rval.append( ld )
            return rval

        try:
            decoded_folder_id = trans.security.decode_id( folder_id[-16:] )
        except TypeError:
            trans.response.status = 400
            return "Malformed folder id ( %s ) specified, unable to decode." % str( folder_id )

        try:
            folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( decoded_folder_id )
            parent_library = folder.parent_library
        except:
            folder = None
            log.error( "FolderContentsController.index: Unable to retrieve folder %s" 
                      % folder_id )

        # TODO: Find the API's path to this folder if necessary.
        # This was needed in recursive descent, but it's not needed
        # for "ls"-style content checking:
        if not folder or not ( trans.user_is_admin() or trans.app.security_agent.can_access_library_item( current_user_roles, folder ) ):
            trans.response.status = 400
            return "Invalid folder id ( %s ) specified." % str( folder_id )

        for content in traverse( folder ):
            encoded_id = trans.security.encode_id( content.id )
            if content.api_type == 'folder':
                encoded_id = 'F' + encoded_id
            rval.append( dict( id = encoded_id,
                               type = content.api_type,
                               name = content.name,
                               # TODO: calculate the folder's library id
                               # (if necessary) and add library_id=X below: 
                               url = url_for( controller='folder_content', id=encoded_id ) ) )
        return rval

    @web.expose_api
    def show( self, trans, id, library_id, **kwd ):
        """
        GET /api/folders/{encoded_folder_id}/
        """
        pass

    @web.expose_api
    def create( self, trans, library_id, payload, **kwd ):
        """
        POST /api/folders/{encoded_folder_id}/contents
        Creates a new folder. This should be superseded by the
        LibraryController.
        """
        pass

    @web.expose_api
    def update( self, trans, id,  library_id, payload, **kwd ):
        """
        PUT /api/folders/{encoded_folder_id}/contents
        """
        pass

    # TODO: Move to library_common.
    def __decode_library_content_id( self, trans, content_id ):
        if ( len( content_id ) % 16 == 0 ):
            return 'LibraryDataset', content_id
        elif ( content_id.startswith( 'F' ) ):
            return 'LibraryFolder', content_id[1:]
        else:
            raise HTTPBadRequest( 'Malformed library content id ( %s ) specified, unable to decode.' % str( content_id ) )
