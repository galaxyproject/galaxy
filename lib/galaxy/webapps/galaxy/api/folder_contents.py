"""
API operations on the contents of a library folder.
"""
from galaxy import util
from galaxy import web
from galaxy import exceptions
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound
from galaxy.web.base.controller import BaseAPIController, UsesLibraryMixin, UsesLibraryMixinItems

import logging
log = logging.getLogger( __name__ )

class FolderContentsController( BaseAPIController, UsesLibraryMixin, UsesLibraryMixinItems ):
    """
    Class controls retrieval, creation and updating of folder contents.
    """

    @expose_api_anonymous
    def index( self, trans, folder_id, **kwd ):
        """
        GET /api/folders/{encoded_folder_id}/contents
        Displays a collection (list) of a folder's contents (files and folders).
        Encoded folder ID is prepended with 'F' if it is a folder as opposed to a data set which does not have it.
        Full path is provided in response as a separate object providing data for breadcrumb path building.
        """

        if ( len( folder_id ) == 17 and folder_id.startswith( 'F' ) ):
            try:
                decoded_folder_id = trans.security.decode_id( folder_id[ 1: ] )
            except TypeError:
                raise exceptions.MalformedId( 'Malformed folder id ( %s ) specified, unable to decode.' % str( folder_id ) )
        else:
            raise exceptions.MalformedId( 'Malformed folder id ( %s ) specified, unable to decode.' % str( folder_id ) )

        try:
            folder = trans.sa_session.query( trans.app.model.LibraryFolder ).filter( trans.app.model.LibraryFolder.table.c.id == decoded_folder_id ).one()
        except MultipleResultsFound:
            raise exceptions.InconsistentDatabase( 'Multiple folders with same id found.' )
        except NoResultFound:
            raise exceptions.ObjectNotFound( 'Folder with the id provided ( %s ) was not found' % str( folder_id ) )
        except Exception:
            raise exceptions.InternalServerError( 'Error loading from the database.' )

        current_user_roles = trans.get_current_user_roles()
        can_add_library_item = trans.user_is_admin() or trans.app.security_agent.can_add_library_item( current_user_roles, folder )

        if not ( trans.user_is_admin() or trans.app.security_agent.can_access_library_item( current_user_roles, folder, trans.user ) ):
            if folder.parent_id == None:
                try:
                    library = trans.sa_session.query( trans.app.model.Library ).filter( trans.app.model.Library.table.c.root_folder_id == decoded_folder_id ).one()
                except Exception:
                    raise exceptions.InternalServerError( 'Error loading from the database.' )
                if trans.app.security_agent.library_is_public( library, contents=False ):
                    pass
                else:
                    if trans.user:
                        log.warning( "SECURITY: User (id: %s) without proper access rights is trying to load folder with ID of %s" % ( trans.user.id, decoded_folder_id ) )
                    else:
                        log.warning( "SECURITY: Anonymous user without proper access rights is trying to load folder with ID of %s" % ( decoded_folder_id ) )
                    raise exceptions.ObjectNotFound( 'Folder with the id provided ( %s ) was not found' % str( folder_id ) ) 
            else:
                if trans.user:
                    log.warning( "SECURITY: User (id: %s) without proper access rights is trying to load folder with ID of %s" % ( trans.user.id, decoded_folder_id ) )
                else:
                    log.warning( "SECURITY: Anonymous user without proper access rights is trying to load folder with ID of %s" % ( decoded_folder_id ) )
                raise exceptions.ObjectNotFound( 'Folder with the id provided ( %s ) was not found' % str( folder_id ) )
        
        path_to_root = []
        def build_path ( folder ):
            """
            Search the path upwards recursively and load the whole route of names and ids for breadcrumb building purposes.
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
        

        folder_contents = []
        time_updated = ''
        time_created = ''
        # Go through every item in the folder and include its meta-data.
        for content_item in self._load_folder_contents( trans, folder ):
            return_item = {}
            encoded_id = trans.security.encode_id( content_item.id )
            time_updated = content_item.update_time.strftime( "%Y-%m-%d %I:%M %p" )
            time_created = content_item.create_time.strftime( "%Y-%m-%d %I:%M %p" )
            
            # For folder return also hierarchy values
            if content_item.api_type == 'folder':
                encoded_id = 'F' + encoded_id
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

        return { 'metadata' : { 'full_path' : full_path, 'can_add_library_item': can_add_library_item }, 'folder_contents' : folder_contents }

    def _load_folder_contents( self, trans, folder ):
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
    def show( self, trans, id, library_id, **kwd ):
        """
        GET /api/folders/{encoded_folder_id}/
        """
        raise exceptions.NotImplemented( 'Showing the library folder content is not implemented.' )

    @web.expose_api
    def create( self, trans, library_id, payload, **kwd ):
        """
        POST /api/folders/{encoded_folder_id}/contents
        Creates a new folder. This should be superseded by the
        LibraryController.
        """
        raise exceptions.NotImplemented( 'Creating the library folder content is not implemented.' )

    @web.expose_api
    def update( self, trans, id,  library_id, payload, **kwd ):
        """
        PUT /api/folders/{encoded_folder_id}/contents
        """
        raise exceptions.NotImplemented( 'Updating the library folder content is not implemented.' )

    # TODO: Move to library_common.
    # def __decode_library_content_id( self, trans, content_id ):
    #     if ( len( content_id ) % 16 == 0 ):
    #         return 'LibraryDataset', content_id
    #     elif ( content_id.startswith( 'F' ) ):
    #         return 'LibraryFolder', content_id[1:]
    #     else:
    #         raise HTTPBadRequest( 'Malformed library content id ( %s ) specified, unable to decode.' % str( content_id ) )

