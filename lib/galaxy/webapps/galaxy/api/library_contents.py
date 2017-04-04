"""
API operations on the contents of a data library.
"""
from galaxy import util
from galaxy import web
from galaxy import exceptions
from galaxy import managers
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import BaseAPIController, UsesLibraryMixin, UsesLibraryMixinItems
from galaxy.web.base.controller import HTTPBadRequest, url_for
from galaxy.managers.collections_util import api_payload_to_create_params, dictify_dataset_collection_instance
from galaxy.model import ExtendedMetadata, ExtendedMetadataIndex
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound

import logging
log = logging.getLogger( __name__ )


class LibraryContentsController( BaseAPIController, UsesLibraryMixin, UsesLibraryMixinItems ):

    def __init__( self, app ):
        super( LibraryContentsController, self ).__init__( app )
        self.hda_manager = managers.hdas.HDAManager( app )

    @expose_api
    def index( self, trans, library_id, **kwd ):
        """
        index( self, trans, library_id, **kwd )
        * GET /api/libraries/{library_id}/contents:
            Returns a list of library files and folders.

        .. note:: May be slow! Returns all content traversing recursively through all folders.
        .. seealso:: :class:`galaxy.webapps.galaxy.api.FolderContentsController.index` for a non-recursive solution

        :param  library_id: the encoded id of the library
        :type   library_id: str

        :returns:   list of dictionaries of the form:
            * id:   the encoded id of the library item
            * name: the 'library path'
                or relationship of the library item to the root
            * type: 'file' or 'folder'
            * url:  the url to get detailed information on the library item
        :rtype:     list

        :raises:  MalformedId, InconsistentDatabase, RequestParameterInvalidException, InternalServerError
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
                    subfolder.api_path = folder.api_path + '/' + subfolder.name
                    subfolder.api_type = 'folder'
                    rval.append( subfolder )
                    rval.extend( traverse( subfolder ) )
            for ld in folder.datasets:
                if not admin:
                    can_access = trans.app.security_agent.can_access_dataset(
                        current_user_roles,
                        ld.library_dataset_dataset_association.dataset
                    )
                if (admin or can_access) and not ld.deleted:
                    ld.api_path = folder.api_path + '/' + ld.name
                    ld.api_type = 'file'
                    rval.append( ld )
            return rval
        try:
            decoded_library_id = self.decode_id( library_id )
        except Exception:
            raise exceptions.MalformedId( 'Malformed library id ( %s ) specified, unable to decode.' % library_id )
        try:
            library = trans.sa_session.query( trans.app.model.Library ).filter( trans.app.model.Library.table.c.id == decoded_library_id ).one()
        except MultipleResultsFound:
            raise exceptions.InconsistentDatabase( 'Multiple libraries found with the same id.' )
        except NoResultFound:
            raise exceptions.RequestParameterInvalidException( 'No library found with the id provided.' )
        except Exception as e:
            raise exceptions.InternalServerError( 'Error loading from the database.' + str(e))
        if not ( trans.user_is_admin() or trans.app.security_agent.can_access_library( current_user_roles, library ) ):
            raise exceptions.RequestParameterInvalidException( 'No library found with the id provided.' )
        encoded_id = 'F' + trans.security.encode_id( library.root_folder.id )
        # appending root folder
        rval.append( dict( id=encoded_id,
                           type='folder',
                           name='/',
                           url=url_for( 'library_content', library_id=library_id, id=encoded_id ) ) )
        library.root_folder.api_path = ''
        # appending all other items in the library recursively
        for content in traverse( library.root_folder ):
            encoded_id = trans.security.encode_id( content.id )
            if content.api_type == 'folder':
                encoded_id = 'F' + encoded_id
            rval.append( dict( id=encoded_id,
                               type=content.api_type,
                               name=content.api_path,
                               url=url_for( 'library_content', library_id=library_id, id=encoded_id, ) ) )
        return rval

    @expose_api
    def show( self, trans, id, library_id, **kwd ):
        """
        show( self, trans, id, library_id, **kwd )
        * GET /api/libraries/{library_id}/contents/{id}
            Returns information about library file or folder.

        :param  id:         the encoded id of the library item to return
        :type   id:         str

        :param  library_id: the encoded id of the library that contains this item
        :type   library_id: str

        :returns:   detailed library item information
        :rtype:     dict

        .. seealso::
            :func:`galaxy.model.LibraryDataset.to_dict` and
            :attr:`galaxy.model.LibraryFolder.dict_element_visible_keys`
        """
        class_name, content_id = self.__decode_library_content_id( id )
        if class_name == 'LibraryFolder':
            content = self.get_library_folder( trans, content_id, check_ownership=False, check_accessible=True )
            rval = content.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id } )
            rval[ 'id' ] = 'F' + str( rval[ 'id' ] )
            if rval[ 'parent_id' ] is not None:  # This can happen for root folders.
                rval[ 'parent_id' ] = 'F' + str( trans.security.encode_id( rval[ 'parent_id' ] ) )
            rval[ 'parent_library_id' ] = trans.security.encode_id( rval[ 'parent_library_id' ] )
        else:
            content = self.get_library_dataset( trans, content_id, check_ownership=False, check_accessible=True )
            rval = content.to_dict( view='element')
            rval[ 'id' ] = trans.security.encode_id( rval[ 'id' ] )
            rval[ 'ldda_id' ] = trans.security.encode_id( rval[ 'ldda_id' ] )
            rval[ 'folder_id' ] = 'F' + str( trans.security.encode_id( rval[ 'folder_id' ] ) )
            rval[ 'parent_library_id' ] = trans.security.encode_id( rval[ 'parent_library_id' ] )
        return rval

    @web.expose_api
    def create( self, trans, library_id, payload, **kwd ):
        """
        create( self, trans, library_id, payload, **kwd )
        * POST /api/libraries/{library_id}/contents:
            create a new library file or folder

        To copy an HDA into a library send ``create_type`` of 'file' and
        the HDA's encoded id in ``from_hda_id`` (and optionally ``ldda_message``).

        To copy an HDCA into a library send ``create_type`` of 'file' and
        the HDCA's encoded id in ``from_hdca_id`` (and optionally ``ldda_message``).

        :type   library_id: str
        :param  library_id: the encoded id of the library where to create the new item
        :type   payload:    dict
        :param  payload:    dictionary structure containing:

            * folder_id:    the encoded id of the parent folder of the new item
            * create_type:  the type of item to create ('file', 'folder' or 'collection')
            * from_hda_id:  (optional, only if create_type is 'file') the
                encoded id of an accessible HDA to copy into the library
            * ldda_message: (optional) the new message attribute of the LDDA created
            * extended_metadata: (optional) sub-dictionary containing any extended
                metadata to associate with the item
            * upload_option: (optional) one of 'upload_file' (default), 'upload_directory' or 'upload_paths'
            * server_dir: (optional, only if upload_option is
                'upload_directory') relative path of the subdirectory of Galaxy
                ``library_import_dir`` to upload. All and only the files (i.e.
                no subdirectories) contained in the specified directory will be
                uploaded.
            * filesystem_paths: (optional, only if upload_option is
                'upload_paths' and the user is an admin) file paths on the
                Galaxy server to upload to the library, one file per line
            * link_data_only: (optional, only when upload_option is
                'upload_directory' or 'upload_paths') either 'copy_files'
                (default) or 'link_to_files'. Setting to 'link_to_files'
                symlinks instead of copying the files
            * name: (optional, only if create_type is 'folder') name of the
                folder to create
            * description: (optional, only if create_type is 'folder')
                description of the folder to create

        :returns:   a dictionary describing the new item unless ``from_hdca_id`` is supplied,
                    in that case a list of such dictionaries is returned.
        :rtype:     object
        """
        if 'create_type' not in payload:
            trans.response.status = 400
            return "Missing required 'create_type' parameter."
        else:
            create_type = payload.pop( 'create_type' )
        if create_type not in ( 'file', 'folder', 'collection' ):
            trans.response.status = 400
            return "Invalid value for 'create_type' parameter ( %s ) specified." % create_type

        if 'folder_id' not in payload:
            trans.response.status = 400
            return "Missing required 'folder_id' parameter."
        else:
            folder_id = payload.pop( 'folder_id' )
            class_name, folder_id = self.__decode_library_content_id( folder_id )
        try:
            # security is checked in the downstream controller
            parent = self.get_library_folder( trans, folder_id, check_ownership=False, check_accessible=False )
        except Exception as e:
            return str( e )
        # The rest of the security happens in the library_common controller.
        real_folder_id = trans.security.encode_id( parent.id )

        # are we copying an HDA to the library folder?
        #   we'll need the id and any message to attach, then branch to that private function
        from_hda_id, from_hdca_id, ldda_message = ( payload.pop( 'from_hda_id', None ), payload.pop( 'from_hdca_id', None ), payload.pop( 'ldda_message', '' ) )
        if create_type == 'file':
            if from_hda_id:
                return self._copy_hda_to_library_folder( trans, self.hda_manager, self.decode_id(from_hda_id), real_folder_id, ldda_message )
            if from_hdca_id:
                return self._copy_hdca_to_library_folder(trans, self.hda_manager, self.decode_id(from_hdca_id), real_folder_id, ldda_message)

        # check for extended metadata, store it and pop it out of the param
        # otherwise sanitize_param will have a fit
        ex_meta_payload = payload.pop('extended_metadata', None)

        # Now create the desired content object, either file or folder.
        if create_type == 'file':
            status, output = trans.webapp.controllers['library_common'].upload_library_dataset( trans, 'api', library_id, real_folder_id, **payload )
        elif create_type == 'folder':
            status, output = trans.webapp.controllers['library_common'].create_folder( trans, 'api', real_folder_id, library_id, **payload )
        elif create_type == 'collection':
            # Not delegating to library_common, so need to check access to parent
            # folder here.
            self.check_user_can_add_to_library_item( trans, parent, check_accessible=True )
            create_params = api_payload_to_create_params( payload )
            create_params[ 'parent' ] = parent
            service = trans.app.dataset_collections_service
            dataset_collection_instance = service.create( **create_params )
            return [ dictify_dataset_collection_instance( dataset_collection_instance, security=trans.security, parent=parent ) ]
        if status != 200:
            trans.response.status = status
            return output
        else:
            rval = []
            for v in output.values():
                if ex_meta_payload is not None:
                    # If there is extended metadata, store it, attach it to the dataset, and index it
                    ex_meta = ExtendedMetadata(ex_meta_payload)
                    trans.sa_session.add( ex_meta )
                    v.extended_metadata = ex_meta
                    trans.sa_session.add(v)
                    trans.sa_session.flush()
                    for path, value in self._scan_json_block(ex_meta_payload):
                        meta_i = ExtendedMetadataIndex(ex_meta, path, value)
                        trans.sa_session.add(meta_i)
                    trans.sa_session.flush()
                if type( v ) == trans.app.model.LibraryDatasetDatasetAssociation:
                    v = v.library_dataset
                encoded_id = trans.security.encode_id( v.id )
                if create_type == 'folder':
                    encoded_id = 'F' + encoded_id
                rval.append( dict( id=encoded_id,
                                   name=v.name,
                                   url=url_for( 'library_content', library_id=library_id, id=encoded_id ) ) )
            return rval

    def _scan_json_block(self, meta, prefix=""):
        """
        Scan a json style data structure, and emit all fields and their values.
        Example paths

        Data
        { "data" : [ 1, 2, 3 ] }

        Path:
        /data == [1,2,3]

        /data/[0] == 1

        """
        if isinstance(meta, dict):
            for a in meta:
                for path, value in self._scan_json_block(meta[a], prefix + "/" + a):
                    yield path, value
        elif isinstance(meta, list):
            for i, a in enumerate(meta):
                for path, value in self._scan_json_block(a, prefix + "[%d]" % (i)):
                    yield path, value
        else:
            # BUG: Everything is cast to string, which can lead to false positives
            # for cross type comparisions, ie "True" == True
            yield prefix, ("%s" % (meta)).encode("utf8", errors='replace')

    @web.expose_api
    def update( self, trans, id, library_id, payload, **kwd ):
        """
        update( self, trans, id, library_id, payload, **kwd )
        * PUT /api/libraries/{library_id}/contents/{id}
            create a ImplicitlyConvertedDatasetAssociation
        .. seealso:: :class:`galaxy.model.ImplicitlyConvertedDatasetAssociation`

        :type   id:         str
        :param  id:         the encoded id of the library item to return
        :type   library_id: str
        :param  library_id: the encoded id of the library that contains this item
        :type   payload:    dict
        :param  payload:    dictionary structure containing::
            'converted_dataset_id':

        :rtype:     None
        :returns:   None
        """
        if 'converted_dataset_id' in payload:
            converted_id = payload.pop( 'converted_dataset_id' )
            content = self.get_library_dataset( trans, id, check_ownership=False, check_accessible=False )
            content_conv = self.get_library_dataset( trans, converted_id, check_ownership=False, check_accessible=False )
            assoc = trans.app.model.ImplicitlyConvertedDatasetAssociation( parent=content.library_dataset_dataset_association,
                                                                           dataset=content_conv.library_dataset_dataset_association,
                                                                           file_type=content_conv.library_dataset_dataset_association.extension,
                                                                           metadata_safe=True )
            trans.sa_session.add( assoc )
            trans.sa_session.flush()

    def __decode_library_content_id( self, content_id ):
        if len( content_id ) % 16 == 0:
            return 'LibraryDataset', content_id
        elif content_id.startswith( 'F' ):
            return 'LibraryFolder', content_id[ 1: ]
        else:
            raise HTTPBadRequest( 'Malformed library content id ( %s ) specified, unable to decode.' % str( content_id ) )

    @web.expose_api
    def delete( self, trans, library_id, id, **kwd ):
        """
        delete( self, trans, library_id, id, **kwd )
        * DELETE /api/libraries/{library_id}/contents/{id}
            delete the LibraryDataset with the given ``id``

        :type   id:     str
        :param  id:     the encoded id of the library dataset to delete
        :type   kwd:    dict
        :param  kwd:    (optional) dictionary structure containing:

            * payload:     a dictionary itself containing:
                * purge:   if True, purge the LD

        :rtype:     dict
        :returns:   an error object if an error occurred or a dictionary containing:
            * id:         the encoded id of the library dataset,
            * deleted:    if the library dataset was marked as deleted,
            * purged:     if the library dataset was purged
        """
        # a request body is optional here
        purge = False
        if kwd.get( 'payload', None ):
            purge = util.string_as_bool( kwd['payload'].get( 'purge', False ) )

        rval = { 'id': id }
        try:
            ld = self.get_library_dataset( trans, id, check_ownership=False, check_accessible=True )
            user_is_admin = trans.user_is_admin()
            can_modify = trans.app.security_agent.can_modify_library_item( trans.user.all_roles(), ld )
            log.debug( 'is_admin: %s, can_modify: %s', user_is_admin, can_modify )
            if not ( user_is_admin or can_modify ):
                trans.response.status = 403
                rval.update({ 'error': 'Unauthorized to delete or purge this library dataset' })
                return rval

            ld.deleted = True
            if purge:
                ld.purged = True
                trans.sa_session.add( ld )
                trans.sa_session.flush()

                # TODO: had to change this up a bit from Dataset.user_can_purge
                dataset = ld.library_dataset_dataset_association.dataset
                no_history_assoc = len( dataset.history_associations ) == len( dataset.purged_history_associations )
                no_library_assoc = dataset.library_associations == [ ld.library_dataset_dataset_association ]
                can_purge_dataset = not dataset.purged and no_history_assoc and no_library_assoc

                if can_purge_dataset:
                    try:
                        ld.library_dataset_dataset_association.dataset.full_delete()
                        trans.sa_session.add( ld.dataset )
                    except:
                        pass
                    # flush now to preserve deleted state in case of later interruption
                    trans.sa_session.flush()
                rval[ 'purged' ] = True
            trans.sa_session.flush()
            rval[ 'deleted' ] = True

        except exceptions.httpexceptions.HTTPInternalServerError as http_server_err:
            log.exception( 'Library_contents API, delete: uncaught HTTPInternalServerError: %s, %s\n%s',
                           id, str( kwd ), str( http_server_err ) )
            raise
        except exceptions.httpexceptions.HTTPException:
            raise
        except Exception as exc:
            log.exception( 'library_contents API, delete: uncaught exception: %s, %s\n%s',
                           id, str( kwd ), str( exc ) )
            trans.response.status = 500
            rval.update({ 'error': str( exc ) })
        return rval
