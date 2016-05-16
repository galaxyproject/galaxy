"""
API operations on the contents of a library folder.
"""
from galaxy import util
from galaxy import exceptions
from galaxy import managers
from galaxy.managers import folders
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.web.base.controller import BaseAPIController, UsesLibraryMixin, UsesLibraryMixinItems

import logging
log = logging.getLogger( __name__ )


class FolderContentsController( BaseAPIController, UsesLibraryMixin, UsesLibraryMixinItems ):
    """
    Class controls retrieval, creation and updating of folder contents.
    """

    def __init__( self, app ):
        super( FolderContentsController, self ).__init__( app )
        self.folder_manager = folders.FolderManager()
        self.hda_manager = managers.hdas.HDAManager( app )

    @expose_api_anonymous
    def index( self, trans, folder_id, **kwd ):
        """
        GET /api/folders/{encoded_folder_id}/contents

        Displays a collection (list) of a folder's contents
        (files and folders). Encoded folder ID is prepended
        with 'F' if it is a folder as opposed to a data set
        which does not have it. Full path is provided in
        response as a separate object providing data for
        breadcrumb path building.

        :param  folder_id: encoded ID of the folder which
            contents should be library_dataset_dict
        :type   folder_id: encoded string

        :param kwd: keyword dictionary with other params
        :type  kwd: dict

        :returns: dictionary containing all items and metadata
        :type:    dict

        :raises: MalformedId, InconsistentDatabase, ObjectNotFound,
             InternalServerError
        """
        is_admin = trans.user_is_admin()
        deleted = kwd.get( 'include_deleted', 'missing' )
        current_user_roles = trans.get_current_user_roles()
        try:
            deleted = util.asbool( deleted )
        except ValueError:
            deleted = False

        decoded_folder_id = self.folder_manager.cut_and_decode( trans, folder_id )
        folder = self.folder_manager.get( trans, decoded_folder_id )

        # Special level of security on top of libraries.
        if trans.app.security_agent.can_access_library( current_user_roles, folder.parent_library ) or is_admin:
            pass
        else:
            if trans.user:
                log.warning( "SECURITY: User (id: %s) without proper access rights is trying to load folder with ID of %s" % ( trans.user.id, decoded_folder_id ) )
            else:
                log.warning( "SECURITY: Anonymous user is trying to load restricted folder with ID of %s" % ( decoded_folder_id ) )
            raise exceptions.ObjectNotFound( 'Folder with the id provided ( %s ) was not found' % str( folder_id ) )

        folder_contents = []
        update_time = ''
        create_time = ''
        #  Go through every accessible item (folders, datasets) in the folder and include its metadata.
        for content_item in self._load_folder_contents( trans, folder, deleted ):
            return_item = {}
            encoded_id = trans.security.encode_id( content_item.id )
            update_time = content_item.update_time.strftime( "%Y-%m-%d %I:%M %p" )
            create_time = content_item.create_time.strftime( "%Y-%m-%d %I:%M %p" )

            if content_item.api_type == 'folder':
                encoded_id = 'F' + encoded_id
                can_modify = is_admin or ( trans.user and trans.app.security_agent.can_modify_library_item( current_user_roles, folder ) )
                can_manage = is_admin or ( trans.user and trans.app.security_agent.can_manage_library_item( current_user_roles, folder ) )
                return_item.update( dict( can_modify=can_modify, can_manage=can_manage ) )
                if content_item.description:
                    return_item.update( dict( description=content_item.description ) )

            if content_item.api_type == 'file':
                #  Is the dataset public or private?
                #  When both are False the dataset is 'restricted'
                #  Access rights are checked on the dataset level, not on the ld or ldda level to maintain consistency
                is_unrestricted = trans.app.security_agent.dataset_is_public( content_item.library_dataset_dataset_association.dataset )
                if trans.user and trans.app.security_agent.dataset_is_private_to_user( trans, content_item ):
                    is_private = True
                else:
                    is_private = False

                # Can user manage the permissions on the dataset?
                can_manage = is_admin or (trans.user and trans.app.security_agent.can_manage_dataset( current_user_roles, content_item.library_dataset_dataset_association.dataset ) )

                nice_size = util.nice_size( int( content_item.library_dataset_dataset_association.get_size() ) )

                library_dataset_dict = content_item.to_dict()

                return_item.update( dict( file_ext=library_dataset_dict[ 'file_ext' ],
                                          date_uploaded=library_dataset_dict[ 'date_uploaded' ],
                                          is_unrestricted=is_unrestricted,
                                          is_private=is_private,
                                          can_manage=can_manage,
                                          file_size=nice_size
                                          ) )
                if content_item.library_dataset_dataset_association.message:
                    return_item.update( dict( message=content_item.library_dataset_dataset_association.message ) )

            # For every item include the default metadata
            return_item.update( dict( id=encoded_id,
                                      type=content_item.api_type,
                                      name=content_item.name,
                                      update_time=update_time,
                                      create_time=create_time,
                                      deleted=content_item.deleted
                                      ) )
            folder_contents.append( return_item )

        # Return the reversed path so it starts with the library node.
        full_path = self.build_path( trans, folder )[ ::-1 ]

        # Check whether user can add items to the current folder
        can_add_library_item = is_admin or trans.app.security_agent.can_add_library_item( current_user_roles, folder )

        # Check whether user can modify the current folder
        can_modify_folder = is_admin or trans.app.security_agent.can_modify_library_item( current_user_roles, folder )

        parent_library_id = None
        if folder.parent_library is not None:
            parent_library_id = trans.security.encode_id( folder.parent_library.id )

        metadata = dict( full_path=full_path,
                         can_add_library_item=can_add_library_item,
                         can_modify_folder=can_modify_folder,
                         folder_name=folder.name,
                         folder_description=folder.description,
                         parent_library_id=parent_library_id )
        folder_container = dict( metadata=metadata, folder_contents=folder_contents )
        return folder_container

    def build_path( self, trans, folder ):
        """
        Search the path upwards recursively and load the whole route of
        names and ids for breadcrumb building purposes.

        :param folder: current folder for navigating up
        :param type:   Galaxy LibraryFolder

        :returns:   list consisting of full path to the library
        :type:      list
        """
        path_to_root = []
        # We are almost in root
        if folder.parent_id is None:
            path_to_root.append( ( 'F' + trans.security.encode_id( folder.id ), folder.name ) )
        else:
            # We add the current folder and traverse up one folder.
            path_to_root.append( ( 'F' + trans.security.encode_id( folder.id ), folder.name ) )
            upper_folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( folder.parent_id )
            path_to_root.extend( self.build_path( trans, upper_folder ) )
        return path_to_root

    def _load_folder_contents( self, trans, folder, include_deleted ):
        """
        Loads all contents of the folder (folders and data sets) but only
        in the first level. Include deleted if the flag is set and if the
        user has access to undelete it.

        :param  folder:          the folder which contents are being loaded
        :type   folder:          Galaxy LibraryFolder

        :param  include_deleted: flag, when true the items that are deleted
            and can be undeleted by current user are shown
        :type   include_deleted: boolean

        :returns:   a list containing the requested items
        :type:      list
        """
        current_user_roles = trans.get_current_user_roles()
        is_admin = trans.user_is_admin()
        content_items = []
        for subfolder in folder.folders:
            if subfolder.deleted:
                if include_deleted:
                    if is_admin:
                        # Admins can see all deleted folders.
                        subfolder.api_type = 'folder'
                        content_items.append( subfolder )
                    else:
                        # Users with MODIFY permissions can see deleted folders.
                        can_modify = trans.app.security_agent.can_modify_library_item( current_user_roles, subfolder )
                        if can_modify:
                            subfolder.api_type = 'folder'
                            content_items.append( subfolder )
            else:
                # Undeleted folders are non-restricted for now. The contents are not.
                # TODO decide on restrictions
                subfolder.api_type = 'folder'
                content_items.append( subfolder )
                # if is_admin:
                #     subfolder.api_type = 'folder'
                #     content_items.append( subfolder )
                # else:
                #     can_access, folder_ids = trans.app.security_agent.check_folder_contents( trans.user, current_user_roles, subfolder )
                #     if can_access:
                #         subfolder.api_type = 'folder'
                #         content_items.append( subfolder )

        for dataset in folder.datasets:
            if dataset.deleted:
                if include_deleted:
                    if is_admin:
                        # Admins can see all deleted datasets.
                        dataset.api_type = 'file'
                        content_items.append( dataset )
                    else:
                        # Users with MODIFY permissions on the item can see the deleted item.
                        can_modify = trans.app.security_agent.can_modify_library_item( current_user_roles, dataset )
                        if can_modify:
                            dataset.api_type = 'file'
                            content_items.append( dataset )
            else:
                if is_admin:
                    dataset.api_type = 'file'
                    content_items.append( dataset )
                else:
                    can_access = trans.app.security_agent.can_access_dataset( current_user_roles, dataset.library_dataset_dataset_association.dataset )
                    if can_access:
                        dataset.api_type = 'file'
                        content_items.append( dataset )

        return content_items

    @expose_api
    def create( self, trans, encoded_folder_id, payload, **kwd ):
        """
        * POST /api/folders/{encoded_id}/contents
            create a new library file from an HDA

        :param  encoded_folder_id:      the encoded id of the folder to import dataset(s) to
        :type   encoded_folder_id:      an encoded id string
        :param  payload:    dictionary structure containing:
            :param from_hda_id:         (optional) the id of an accessible HDA to copy into the library
            :type  from_hda_id:         encoded id
            :param ldda_message:        (optional) the new message attribute of the LDDA created
            :type   ldda_message:       str
            :param extended_metadata:   (optional) dub-dictionary containing any extended metadata to associate with the item
            :type  extended_metadata:   dict
        :type   payload:    dict

        :returns:   a dictionary containing the id, name, and 'show' url of the new item
        :rtype:     dict

        :raises:    ObjectAttributeInvalidException,
            InsufficientPermissionsException, ItemAccessibilityException,
            InternalServerError
        """
        encoded_folder_id_16 = self.__decode_library_content_id( trans, encoded_folder_id )
        from_hda_id, ldda_message = ( payload.pop( 'from_hda_id', None ), payload.pop( 'ldda_message', '' ) )
        if ldda_message:
            ldda_message = util.sanitize_html.sanitize_html( ldda_message, 'utf-8' )
        rval = {}
        try:
            decoded_hda_id = self.decode_id( from_hda_id )
            hda = self.hda_manager.get_owned( decoded_hda_id, trans.user, current_history=trans.history )
            hda = self.hda_manager.error_if_uploading( hda )
            folder = self.get_library_folder( trans, encoded_folder_id_16, check_accessible=True )

            library = folder.parent_library
            if library.deleted:
                raise exceptions.ObjectAttributeInvalidException()
            if not self.can_current_user_add_to_library_item( trans, folder ):
                raise exceptions.InsufficientPermissionsException()

            ldda = self.copy_hda_to_library_folder( trans, hda, folder, ldda_message=ldda_message )
            update_time = ldda.update_time.strftime( "%Y-%m-%d %I:%M %p" )
            ldda_dict = ldda.to_dict()
            rval = trans.security.encode_dict_ids( ldda_dict )
            rval['update_time'] = update_time

        except exceptions.ObjectAttributeInvalidException:
            raise exceptions.ObjectAttributeInvalidException( 'You cannot add datasets into deleted library. Undelete it first.' )
        except exceptions.InsufficientPermissionsException:
            raise exceptions.exceptions.InsufficientPermissionsException( 'You do not have proper permissions to add a dataset to a folder with id (%s)' % ( encoded_folder_id ) )
        except Exception as exc:
            # TODO handle exceptions better within the mixins
            if ( ( 'not accessible to the current user' in str( exc ) ) or ( 'You are not allowed to access this dataset' in str( exc ) ) ):
                raise exceptions.ItemAccessibilityException( 'You do not have access to the requested item' )
            else:
                log.exception( exc )
                raise exceptions.InternalServerError( 'An unknown error ocurred. Please try again.' )
        return rval

    def __decode_library_content_id( self, trans, encoded_folder_id ):
        """
        Identifies whether the id provided is properly encoded
        LibraryFolder.

        :param  encoded_folder_id:  encoded id of Galaxy LibraryFolder
        :type   encoded_folder_id:  encoded string

        :returns:   encoded id of Folder (had 'F' prepended)
        :type:  string

        :raises:    MalformedId
        """
        if ( ( len( encoded_folder_id ) % 16 == 1 ) and encoded_folder_id.startswith( 'F' ) ):
            return encoded_folder_id[ 1: ]
        else:
            raise exceptions.MalformedId( 'Malformed folder id ( %s ) specified, unable to decode.' % str( encoded_folder_id ) )

    @expose_api
    def show( self, trans, id, library_id, **kwd ):
        """
        GET /api/folders/{encoded_folder_id}/
        """
        raise exceptions.NotImplemented( 'Showing the library folder content is not implemented here.' )

    @expose_api
    def update( self, trans, id, library_id, payload, **kwd ):
        """
        PUT /api/folders/{encoded_folder_id}/contents
        """
        raise exceptions.NotImplemented( 'Updating the library folder content is not implemented here.' )
