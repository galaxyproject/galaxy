"""
API operations on the contents of a folder.
"""
import logging, os, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.orm import *

log = logging.getLogger( __name__ )

class FolderContentsController( BaseAPIController, UsesLibraryMixin, UsesLibraryMixinItems ):
    """
    Class controls retrieval, creation and updating of folder contents.
    """

    def load_folder_contents( self, trans, folder ):
        """
        Loads all contents of the folder (folders and data sets) but only in the first level.
        """
        current_user_roles = trans.get_current_user_roles()
        is_admin = trans.user_is_admin()
        content_items = []
        for subfolder in folder.active_folders:
            if not is_admin:
                can_access, folder_ids = trans.app.security_agent.check_folder_contents( trans.user, current_user_roles, subfolder )
            if (is_admin or can_access) and not subfolder.deleted:
                subfolder.api_type = 'folder'
                content_items.append( subfolder )
        for dataset in folder.datasets:
            if not is_admin:
                can_access = trans.app.security_agent.can_access_dataset( current_user_roles, dataset.library_dataset_dataset_association.dataset )
            if (is_admin or can_access) and not dataset.deleted:
                dataset.api_type = 'file'
                content_items.append( dataset )
        return content_items

    @web.expose_api
    def index( self, trans, folder_id, **kwd ):
        """
        GET /api/folders/{encoded_folder_id}/contents
        Displays a collection (list) of a folder's contents (files and folders).
        Encoded folder ID is prepended with 'F' if it is a folder as opposed to a data set which does not have it.
        Full path is provided as a separate object in response providing data for breadcrumb path building.
        """
        folder_container = []
        current_user_roles = trans.get_current_user_roles()

        if ( folder_id.startswith( 'F' ) ):
            try:
                decoded_folder_id = trans.security.decode_id( folder_id[1:] )
            except TypeError:
                trans.response.status = 400
                return "Malformed folder id ( %s ) specified, unable to decode." % str( folder_id )

        try:
            folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( decoded_folder_id )
        except:
            folder = None
            log.error( "FolderContentsController.index: Unable to retrieve folder with ID: %s" % folder_id )

        # We didn't find the folder or user does not have an access to it.
        if not folder:
            trans.response.status = 400
            return "Invalid folder id ( %s ) specified." % str( folder_id )
        
        if not ( trans.user_is_admin() or trans.app.security_agent.can_access_library_item( current_user_roles, folder, trans.user ) ):
            log.warning( "SECURITY: User (id: %s) without proper access rights is trying to load folder with ID of %s" % ( trans.user.id, folder.id ) )
            trans.response.status = 400
            return "Invalid folder id ( %s ) specified." % str( folder_id )
        
        path_to_root = []
        def build_path ( folder ):
            """
            Search the path upwards recursively and load the whole route of names and ids for breadcrumb purposes.
            """
            path_to_root = []
            # We are almost in root
            if folder.parent_id is None:
                path_to_root.append( ( 'F' + trans.security.encode_id( folder.id ), folder.name ) )
            else:
            # We add the current folder and traverse up one folder.
                path_to_root.append( ( 'F' + trans.security.encode_id( folder.id ), folder.name ) )
                upper_folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( folder.parent_id )
                path_to_root.extend( build_path( upper_folder ) )
            return path_to_root
            
        # Return the reversed path so it starts with the library node.
        full_path = build_path( folder )[::-1]
        folder_container.append( dict( full_path = full_path ) )
        
        folder_contents = []
        time_updated = ''
        time_created = ''
        # Go through every item in the folder and include its meta-data.
        for content_item in self.load_folder_contents( trans, folder ):
#             rval = content_item.to_dict()
            return_item = {}
            encoded_id = trans.security.encode_id( content_item.id )
            time_updated = content_item.update_time.strftime( "%Y-%m-%d %I:%M %p" )
            time_created = content_item.create_time.strftime( "%Y-%m-%d %I:%M %p" )
            
            # For folder return also hierarchy values
            if content_item.api_type == 'folder':
                encoded_id = 'F' + encoded_id
#                 time_updated = content_item.update_time.strftime( "%Y-%m-%d %I:%M %p" )
                return_item.update ( dict ( item_count = content_item.item_count ) )

            if content_item.api_type == 'file':
                library_dataset_dict = content_item.to_dict()
                library_dataset_dict['data_type']
                library_dataset_dict['file_size']
                library_dataset_dict['date_uploaded']
                return_item.update ( dict ( data_type = library_dataset_dict['data_type'],
                                            file_size = library_dataset_dict['file_size'],
                                            date_uploaded = library_dataset_dict['date_uploaded'] ) )

            # For every item return also the default meta-data
            return_item.update( dict( id = encoded_id,
                               type = content_item.api_type,
                               name = content_item.name,
                               time_updated = time_updated,
                               time_created = time_created
                                ) )
            folder_contents.append( return_item )
        # Put the data in the container
        folder_container.append( dict( folder_contents = folder_contents ) )
        return folder_container

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
