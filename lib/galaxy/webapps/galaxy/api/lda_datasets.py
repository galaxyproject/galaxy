"""
API operations on the library datasets.
"""
import glob
import logging
import os
import os.path
import string
import sys
import tempfile
import zipfile
from json import dumps

from paste.httpexceptions import HTTPBadRequest, HTTPInternalServerError

from galaxy import exceptions
from galaxy import util
from galaxy import web
from galaxy.exceptions import ObjectNotFound
from galaxy.managers import folders, roles
from galaxy.tools.actions import upload_common
from galaxy.util.streamball import StreamBall
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.web.base.controller import BaseAPIController, UsesVisualizationMixin

log = logging.getLogger( __name__ )


class LibraryDatasetsController( BaseAPIController, UsesVisualizationMixin ):

    def __init__( self, app ):
        super( LibraryDatasetsController, self ).__init__( app )
        self.folder_manager = folders.FolderManager()
        self.role_manager = roles.RoleManager( app )

    @expose_api_anonymous
    def show( self, trans, id, **kwd ):
        """
        show( self, trans, id, **kwd )
        * GET /api/libraries/datasets/{encoded_dataset_id}
            Displays information about the dataset identified by the encoded ID.

        :param  id:      the encoded id of the dataset to query
        :type   id:      an encoded id string

        :returns:   detailed dataset information from base controller
        :rtype:     dictionary

        .. seealso:: :attr:`galaxy.web.base.controller.UsesLibraryMixinItems.get_library_dataset`
        """
        try:
            library_dataset = self.get_library_dataset( trans, id=id, check_ownership=False, check_accessible=True )
        except Exception:
            raise exceptions.ObjectNotFound( 'Requested library_dataset was not found.' )

        current_user_roles = trans.get_current_user_roles()

        # Build the full path for breadcrumb purposes.
        full_path = self._build_path( trans, library_dataset.folder )
        dataset_item = ( trans.security.encode_id( library_dataset.id ), library_dataset.name )
        full_path.insert(0, dataset_item)
        full_path = full_path[ ::-1 ]

        # Find expired versions of the library dataset
        expired_ldda_versions = []
        for expired_ldda in library_dataset.expired_datasets:
            expired_ldda_versions.append( ( trans.security.encode_id( expired_ldda.id ), expired_ldda.name ) )

        rval = trans.security.encode_all_ids( library_dataset.to_dict() )
        if len(expired_ldda_versions) > 0:
            rval[ 'has_versions' ] = True
            rval[ 'expired_versions' ] = expired_ldda_versions
        rval[ 'deleted' ] = library_dataset.deleted
        rval[ 'folder_id' ] = 'F' + rval[ 'folder_id' ]
        rval[ 'full_path' ] = full_path
        rval[ 'file_size' ] = util.nice_size( int( library_dataset.library_dataset_dataset_association.get_size() ) )
        rval[ 'date_uploaded' ] = library_dataset.library_dataset_dataset_association.create_time.strftime( "%Y-%m-%d %I:%M %p" )
        rval[ 'can_user_modify' ] = trans.app.security_agent.can_modify_library_item( current_user_roles, library_dataset) or trans.user_is_admin()
        rval[ 'is_unrestricted' ] = trans.app.security_agent.dataset_is_public( library_dataset.library_dataset_dataset_association.dataset )

        #  Manage dataset permission is always attached to the dataset itself, not the the ld or ldda to maintain consistency
        rval[ 'can_user_manage' ] = trans.app.security_agent.can_manage_dataset( current_user_roles, library_dataset.library_dataset_dataset_association.dataset) or trans.user_is_admin()
        return rval

    @expose_api_anonymous
    def show_version( self, trans, encoded_dataset_id, encoded_ldda_id, **kwd ):
        """
        show_version( self, trans, encoded_dataset_id, encoded_ldda_id, **kwd ):
        * GET /api/libraries/datasets/{encoded_dataset_id}/versions/{encoded_ldda_id}
            Displays information about specific version of the library_dataset (i.e. ldda).

        :param  encoded_dataset_id:      the encoded id of the dataset to query
        :type   encoded_dataset_id:      an encoded id string

        :param  encoded_ldda_id:      the encoded id of the ldda to query
        :type   encoded_ldda_id:      an encoded id string

        :rtype:     dictionary
        :returns:   dict of ldda's details
        """
        try:
            library_dataset = self.get_library_dataset( trans, id=encoded_dataset_id, check_ownership=False, check_accessible=True )
        except Exception:
            raise exceptions.ObjectNotFound( 'Requested library_dataset was not found.' )

        try:
            ldda = self.get_library_dataset_dataset_association( trans, id=encoded_ldda_id, check_ownership=False, check_accessible=False )
        except Exception as e:
            raise exceptions.ObjectNotFound( 'Requested version of library dataset was not found.' + str(e) )

        if ldda not in library_dataset.expired_datasets:
            raise exceptions.ObjectNotFound( 'Given library dataset does not have the requested version.' )

        rval = trans.security.encode_all_ids( ldda.to_dict() )
        return rval

    @expose_api
    def show_roles( self, trans, encoded_dataset_id, **kwd ):
        """
        show_roles( self, trans, id, **kwd ):
        * GET /api/libraries/datasets/{encoded_dataset_id}/permissions
            Displays information about current or available roles
            for a given dataset permission.

        :param  encoded_dataset_id:      the encoded id of the dataset to query
        :type   encoded_dataset_id:      an encoded id string

        :param  scope:      either 'current' or 'available'
        :type   scope:      string

        :rtype:     dictionary
        :returns:   either dict of current roles for all permission types or
                           dict of available roles to choose from (is the same for any permission type)
        """

        current_user_roles = trans.get_current_user_roles()
        try:
            library_dataset = self.get_library_dataset( trans, id=encoded_dataset_id, check_ownership=False, check_accessible=False )
        except Exception as e:
            raise exceptions.ObjectNotFound( 'Requested dataset was not found.' + str(e) )
        dataset = library_dataset.library_dataset_dataset_association.dataset

        # User has to have manage permissions permission in order to see the roles.
        can_manage = trans.app.security_agent.can_manage_dataset( current_user_roles, dataset ) or trans.user_is_admin()
        if not can_manage:
            raise exceptions.InsufficientPermissionsException( 'You do not have proper permission to access permissions.' )

        scope = kwd.get( 'scope', None )
        if scope == 'current' or scope is None:
            return self._get_current_roles( trans, library_dataset )

        #  Return roles that are available to select.
        elif scope == 'available':
            page = kwd.get( 'page', None )
            if page is not None:
                page = int( page )
            else:
                page = 1

            page_limit = kwd.get( 'page_limit', None )
            if page_limit is not None:
                page_limit = int( page_limit )
            else:
                page_limit = 10

            query = kwd.get( 'q', None )

            roles, total_roles = trans.app.security_agent.get_valid_roles( trans, dataset, query, page, page_limit )

            return_roles = []
            for role in roles:
                role_id = trans.security.encode_id( role.id )
                return_roles.append( dict( id=role_id, name=role.name, type=role.type ) )
            return dict( roles=return_roles, page=page, page_limit=page_limit, total=total_roles )
        else:
            raise exceptions.RequestParameterInvalidException( "The value of 'scope' parameter is invalid. Alllowed values: current, available" )

    def _get_current_roles( self, trans, library_dataset):
        """
        Find all roles currently connected to relevant permissions
        on the library dataset and the underlying dataset.

        :param  library_dataset:      the model object
        :type   library_dataset:      LibraryDataset

        :rtype:     dictionary
        :returns:   dict of current roles for all available permission types
        """
        dataset = library_dataset.library_dataset_dataset_association.dataset

        # Omit duplicated roles by converting to set
        access_roles = set( dataset.get_access_roles( trans ) )
        modify_roles = set( trans.app.security_agent.get_roles_for_action( library_dataset, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY ) )
        manage_roles = set( dataset.get_manage_permissions_roles( trans ) )

        access_dataset_role_list = [ ( access_role.name, trans.security.encode_id( access_role.id ) ) for access_role in access_roles ]
        manage_dataset_role_list = [ ( manage_role.name, trans.security.encode_id( manage_role.id ) ) for manage_role in manage_roles ]
        modify_item_role_list = [ ( modify_role.name, trans.security.encode_id( modify_role.id ) ) for modify_role in modify_roles ]

        return dict( access_dataset_roles=access_dataset_role_list, modify_item_roles=modify_item_role_list, manage_dataset_roles=manage_dataset_role_list )

    @expose_api
    def update_permissions( self, trans, encoded_dataset_id, payload=None, **kwd ):
        """
        *POST /api/libraries/datasets/{encoded_dataset_id}/permissions
            Set permissions of the given dataset to the given role ids.

        :param  encoded_dataset_id:      the encoded id of the dataset to update permissions of
        :type   encoded_dataset_id:      an encoded id string
        :param   payload: dictionary structure containing:
            :param  action:     (required) describes what action should be performed
                                available actions: make_private, remove_restrictions, set_permissions
            :type   action:     string
            :param  access_ids[]:      list of Role.id defining roles that should have access permission on the dataset
            :type   access_ids[]:      string or list
            :param  manage_ids[]:      list of Role.id defining roles that should have manage permission on the dataset
            :type   manage_ids[]:      string or list
            :param  modify_ids[]:      list of Role.id defining roles that should have modify permission on the library dataset item
            :type   modify_ids[]:      string or list
        :type:      dictionary
        :returns:   dict of current roles for all available permission types
        :rtype:     dictionary

        :raises: RequestParameterInvalidException, ObjectNotFound, InsufficientPermissionsException, InternalServerError
                    RequestParameterMissingException
        """
        if payload:
            kwd.update(payload)
        try:
            library_dataset = self.get_library_dataset( trans, id=encoded_dataset_id, check_ownership=False, check_accessible=False )
        except Exception as e:
            raise exceptions.ObjectNotFound( 'Requested dataset was not found.' + str(e) )
        dataset = library_dataset.library_dataset_dataset_association.dataset
        current_user_roles = trans.get_current_user_roles()
        can_manage = trans.app.security_agent.can_manage_dataset( current_user_roles, dataset ) or trans.user_is_admin()
        if not can_manage:
            raise exceptions.InsufficientPermissionsException( 'You do not have proper permissions to manage permissions on this dataset.' )
        new_access_roles_ids = util.listify( kwd.get( 'access_ids[]', None ) )
        new_manage_roles_ids = util.listify( kwd.get( 'manage_ids[]', None ) )
        new_modify_roles_ids = util.listify( kwd.get( 'modify_ids[]', None ) )
        action = kwd.get( 'action', None )
        if action is None:
            raise exceptions.RequestParameterMissingException( 'The mandatory parameter "action" is missing.' )
        elif action == 'remove_restrictions':
            trans.app.security_agent.make_dataset_public( dataset )
            if not trans.app.security_agent.dataset_is_public( dataset ):
                raise exceptions.InternalServerError( 'An error occured while making dataset public.' )
        elif action == 'make_private':
            if not trans.app.security_agent.dataset_is_private_to_user( trans, library_dataset ):
                private_role = trans.app.security_agent.get_private_user_role( trans.user )
                dp = trans.app.model.DatasetPermissions( trans.app.security_agent.permitted_actions.DATASET_ACCESS.action, dataset, private_role )
                trans.sa_session.add( dp )
                trans.sa_session.flush()
            if not trans.app.security_agent.dataset_is_private_to_user( trans, library_dataset ):
                # Check again and inform the user if dataset is not private.
                raise exceptions.InternalServerError( 'An error occured and the dataset is NOT private.' )
        elif action == 'set_permissions':
            # ACCESS DATASET ROLES
            valid_access_roles = []
            invalid_access_roles_ids = []
            if new_access_roles_ids is None:
                trans.app.security_agent.make_dataset_public( dataset )
            else:
                for role_id in new_access_roles_ids:
                    role = self.role_manager.get( trans, self.__decode_id( trans, role_id, 'role' ) )
                    #  Check whether role is in the set of allowed roles
                    valid_roles, total_roles = trans.app.security_agent.get_valid_roles( trans, dataset )
                    if role in valid_roles:
                        valid_access_roles.append( role )
                    else:
                        invalid_access_roles_ids.append( role_id )
                if len( invalid_access_roles_ids ) > 0:
                    log.warning( "The following roles could not be added to the dataset access permission: " + str( invalid_access_roles_ids ) )

                access_permission = dict( access=valid_access_roles )
                trans.app.security_agent.set_dataset_permission( dataset, access_permission )

            # MANAGE DATASET ROLES
            valid_manage_roles = []
            invalid_manage_roles_ids = []
            new_manage_roles_ids = util.listify( new_manage_roles_ids )

            #  Load all access roles to check
            active_access_roles = dataset.get_access_roles( trans )

            for role_id in new_manage_roles_ids:
                role = self.role_manager.get( trans, self.__decode_id( trans, role_id, 'role' ) )
                #  Check whether role is in the set of access roles
                if role in active_access_roles:
                    valid_manage_roles.append( role )
                else:
                    invalid_manage_roles_ids.append( role_id )

            if len( invalid_manage_roles_ids ) > 0:
                log.warning( "The following roles could not be added to the dataset manage permission: " + str( invalid_manage_roles_ids ) )

            manage_permission = { trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS: valid_manage_roles }
            trans.app.security_agent.set_dataset_permission( dataset, manage_permission )

            # MODIFY LIBRARY ITEM ROLES
            valid_modify_roles = []
            invalid_modify_roles_ids = []
            new_modify_roles_ids = util.listify( new_modify_roles_ids )

            #  Load all access roles to check
            active_access_roles = dataset.get_access_roles( trans )

            for role_id in new_modify_roles_ids:
                role = self.role_manager.get( trans, self.__decode_id( trans, role_id, 'role' ) )
                #  Check whether role is in the set of access roles
                if role in active_access_roles:
                    valid_modify_roles.append( role )
                else:
                    invalid_modify_roles_ids.append( role_id )

            if len( invalid_modify_roles_ids ) > 0:
                log.warning( "The following roles could not be added to the dataset modify permission: " + str( invalid_modify_roles_ids ) )

            modify_permission = { trans.app.security_agent.permitted_actions.LIBRARY_MODIFY: valid_modify_roles }
            trans.app.security_agent.set_library_item_permission( library_dataset, modify_permission )

        else:
            raise exceptions.RequestParameterInvalidException( 'The mandatory parameter "action" has an invalid value. '
                                                               'Allowed values are: "remove_restrictions", "make_private", "set_permissions"' )

        return self._get_current_roles( trans, library_dataset )

    @expose_api
    def delete( self, trans, encoded_dataset_id, **kwd ):
        """
        delete( self, trans, encoded_dataset_id, **kwd ):
        * DELETE /api/libraries/datasets/{encoded_dataset_id}
            Marks the dataset deleted or undeleted based on the value
            of the undelete flag.
            If the flag is not present it is considered False and the
            item is marked deleted.

        :param  encoded_dataset_id:      the encoded id of the dataset to change
        :type   encoded_dataset_id:      an encoded id string

        :returns:   dict containing information about the dataset
        :rtype:     dictionary
        """
        undelete = util.string_as_bool( kwd.get( 'undelete', False ) )
        try:
            dataset = self.get_library_dataset( trans, id=encoded_dataset_id, check_ownership=False, check_accessible=False )
        except Exception as e:
            raise exceptions.ObjectNotFound( 'Requested dataset was not found.' + str(e) )
        current_user_roles = trans.get_current_user_roles()
        allowed = trans.app.security_agent.can_modify_library_item( current_user_roles, dataset )
        if ( not allowed ) and ( not trans.user_is_admin() ):
            raise exceptions.InsufficientPermissionsException( 'You do not have proper permissions to delete this dataset.')

        if undelete:
            dataset.deleted = False
        else:
            dataset.deleted = True

        trans.sa_session.add( dataset )
        trans.sa_session.flush()

        rval = trans.security.encode_all_ids( dataset.to_dict() )
        nice_size = util.nice_size( int( dataset.library_dataset_dataset_association.get_size() ) )
        rval[ 'file_size' ] = nice_size
        rval[ 'update_time' ] = dataset.update_time.strftime( "%Y-%m-%d %I:%M %p" )
        rval[ 'deleted' ] = dataset.deleted
        rval[ 'folder_id' ] = 'F' + rval[ 'folder_id' ]
        return rval

    @expose_api
    def load( self, trans, payload=None, **kwd ):
        """
        * POST /api/libraries/datasets
        Load dataset from the given source into the library.
        Source can be:
            user directory - root folder specified in galaxy.ini as "$user_library_import_dir"
                example path: path/to/galaxy/$user_library_import_dir/user@example.com/{user can browse everything here}
                the folder with the user login has to be created beforehand
            (admin)import directory - root folder specified in galaxy ini as "$library_import_dir"
                example path: path/to/galaxy/$library_import_dir/{admin can browse everything here}
            (admin)any absolute or relative path - option allowed with "allow_library_path_paste" in galaxy.ini

        :param   payload: dictionary structure containing:
            :param  encoded_folder_id:      the encoded id of the folder to import dataset(s) to
            :type   encoded_folder_id:      an encoded id string
            :param  source:                 source the datasets should be loaded from
            :type   source:                 str
            :param  link_data:              flag whether to link the dataset to data or copy it to Galaxy, defaults to copy
                                            while linking is set to True all symlinks will be resolved _once_
            :type   link_data:              bool
            :param  preserve_dirs:          flag whether to preserve the directory structure when importing dir
                                            if False only datasets will be imported
            :type   preserve_dirs:          bool
            :param  file_type:              file type of the loaded datasets, defaults to 'auto' (autodetect)
            :type   file_type:              str
            :param  dbkey:                  dbkey of the loaded genome, defaults to '?' (unknown)
            :type   dbkey:                  str
        :type   dictionary
        :returns:   dict containing information about the created upload job
        :rtype:     dictionary
        :raises: RequestParameterMissingException, AdminRequiredException, ConfigDoesNotAllowException, RequestParameterInvalidException
                    InsufficientPermissionsException, ObjectNotFound
        """
        if payload:
            kwd.update(payload)
        kwd['space_to_tab'] = False
        kwd['to_posix_lines'] = True
        kwd[ 'dbkey' ] = kwd.get( 'dbkey', '?' )
        kwd[ 'file_type' ] = kwd.get( 'file_type', 'auto' )
        kwd['link_data_only'] = 'link_to_files' if util.string_as_bool( kwd.get( 'link_data', False ) ) else 'copy_files'
        encoded_folder_id = kwd.get( 'encoded_folder_id', None )
        if encoded_folder_id is not None:
            folder_id = self.folder_manager.cut_and_decode( trans, encoded_folder_id )
        else:
            raise exceptions.RequestParameterMissingException( 'The required atribute encoded_folder_id is missing.' )
        path = kwd.get( 'path', None)
        if path is None:
            raise exceptions.RequestParameterMissingException( 'The required atribute path is missing.' )
        folder = self.folder_manager.get( trans, folder_id )

        source = kwd.get( 'source', None )
        if source not in [ 'userdir_file', 'userdir_folder', 'importdir_file', 'importdir_folder', 'admin_path' ]:
            raise exceptions.RequestParameterMissingException( 'You have to specify "source" parameter. Possible values are "userdir_file", "userdir_folder", "admin_path", "importdir_file" and "importdir_folder". ')
        if source in [ 'importdir_file', 'importdir_folder' ]:
            if not trans.user_is_admin:
                raise exceptions.AdminRequiredException( 'Only admins can import from importdir.' )
            if not trans.app.config.library_import_dir:
                raise exceptions.ConfigDoesNotAllowException( 'The configuration of this Galaxy instance does not allow admins to import into library from importdir.' )
            import_base_dir = trans.app.config.library_import_dir
            path = os.path.join( import_base_dir, path )
        if source in [ 'userdir_file', 'userdir_folder' ]:
            user_login = trans.user.email
            user_base_dir = trans.app.config.user_library_import_dir
            if user_base_dir is None:
                raise exceptions.ConfigDoesNotAllowException( 'The configuration of this Galaxy instance does not allow upload from user directories.' )
            full_dir = os.path.join( user_base_dir, user_login )
            if not path.lower().startswith( full_dir.lower() ):
                path = os.path.join( full_dir, path )
            if not os.path.exists( path ):
                raise exceptions.RequestParameterInvalidException( 'Given path does not exist on the host.' )
            if not self.folder_manager.can_add_item( trans, folder ):
                raise exceptions.InsufficientPermissionsException( 'You do not have proper permission to add items to the given folder.' )
        if source == 'admin_path':
            if not trans.app.config.allow_library_path_paste:
                raise exceptions.ConfigDoesNotAllowException( 'The configuration of this Galaxy instance does not allow admins to import into library from path.' )
            if not trans.user_is_admin:
                raise exceptions.AdminRequiredException( 'Only admins can import from path.' )

        # Set up the traditional tool state/params
        tool_id = 'upload1'
        tool = trans.app.toolbox.get_tool( tool_id )
        state = tool.new_state( trans )
        tool.populate_state( trans, tool.inputs, kwd, state.inputs )
        tool_params = state.inputs
        dataset_upload_inputs = []
        for input in tool.inputs.itervalues():
            if input.type == "upload_dataset":
                dataset_upload_inputs.append( input )
        library_bunch = upload_common.handle_library_params( trans, {}, trans.security.encode_id( folder.id ) )
        abspath_datasets = []
        kwd[ 'filesystem_paths' ] = path
        if source in [ 'importdir_folder' ]:
            kwd[ 'filesystem_paths' ] = os.path.join( import_base_dir, path )
        # user wants to import one file only
        if source in [ "userdir_file", "importdir_file" ]:
            file = os.path.abspath( path )
            abspath_datasets.append( trans.webapp.controllers[ 'library_common' ].make_library_uploaded_dataset(
                trans, 'api', kwd, os.path.basename( file ), file, 'server_dir', library_bunch ) )
        # user wants to import whole folder
        if source == "userdir_folder":
            uploaded_datasets_bunch = trans.webapp.controllers[ 'library_common' ].get_path_paste_uploaded_datasets(
                trans, 'api', kwd, library_bunch, 200, '' )
            uploaded_datasets = uploaded_datasets_bunch[ 0 ]
            if uploaded_datasets is None:
                raise exceptions.ObjectNotFound( 'Given folder does not contain any datasets.' )
            for ud in uploaded_datasets:
                ud.path = os.path.abspath( ud.path )
                abspath_datasets.append( ud )
        #  user wants to import from path
        if source in [ "admin_path", "importdir_folder" ]:
            # validate the path is within root
            uploaded_datasets_bunch = trans.webapp.controllers[ 'library_common' ].get_path_paste_uploaded_datasets(
                trans, 'api', kwd, library_bunch, 200, '' )
            uploaded_datasets = uploaded_datasets_bunch[0]
            if uploaded_datasets is None:
                raise exceptions.ObjectNotFound( 'Given folder does not contain any datasets.' )
            for ud in uploaded_datasets:
                ud.path = os.path.abspath( ud.path )
                abspath_datasets.append( ud )
        json_file_path = upload_common.create_paramfile( trans, abspath_datasets )
        data_list = [ ud.data for ud in abspath_datasets ]
        job_params = {}
        job_params['link_data_only'] = dumps( kwd.get( 'link_data_only', 'copy_files' ) )
        job_params['uuid'] = dumps( kwd.get( 'uuid', None ) )
        job, output = upload_common.create_job( trans, tool_params, tool, json_file_path, data_list, folder=folder, job_params=job_params )
        trans.sa_session.add( job )
        trans.sa_session.flush()
        job_dict = job.to_dict()
        job_dict[ 'id' ] = trans.security.encode_id( job_dict[ 'id' ] )
        return job_dict

    @web.expose
    #  TODO convert to expose_api
    def download( self, trans, format, **kwd ):
        """
        download( self, trans, format, **kwd )
        * GET /api/libraries/datasets/download/{format}
        * POST /api/libraries/datasets/download/{format}
            Downloads requested datasets (identified by encoded IDs) in requested format.

        example: ``GET localhost:8080/api/libraries/datasets/download/tbz?ld_ids%255B%255D=a0d84b45643a2678&ld_ids%255B%255D=fe38c84dcd46c828``

        .. note:: supported format values are: 'zip', 'tgz', 'tbz', 'uncompressed'

        :param  format:      string representing requested archive format
        :type   format:      string
        :param  ld_ids[]:      an array of encoded dataset ids
        :type   ld_ids[]:      an array
        :param  folder_ids[]:      an array of encoded folder ids
        :type   folder_ids[]:      an array

        :rtype:   file
        :returns: either archive with the requested datasets packed inside or a single uncompressed dataset

        :raises: MessageException, ItemDeletionException, ItemAccessibilityException, HTTPBadRequest, OSError, IOError, ObjectNotFound
        """
        library_datasets = []
        datasets_to_download = kwd.get( 'ld_ids%5B%5D', None )
        if datasets_to_download is None:
            datasets_to_download = kwd.get( 'ld_ids', None )
        if datasets_to_download is not None:
            datasets_to_download = util.listify( datasets_to_download )
            for dataset_id in datasets_to_download:
                try:
                    library_dataset = self.get_library_dataset( trans, id=dataset_id, check_ownership=False, check_accessible=True )
                    library_datasets.append( library_dataset )
                except HTTPBadRequest:
                    raise exceptions.RequestParameterInvalidException( 'Bad Request.' )
                except HTTPInternalServerError:
                    raise exceptions.InternalServerError( 'Internal error.' )
                except Exception as e:
                    raise exceptions.InternalServerError( 'Unknown error.' + str(e) )

        folders_to_download = kwd.get( 'folder_ids%5B%5D', None )
        if folders_to_download is None:
            folders_to_download = kwd.get( 'folder_ids', None )
        if folders_to_download is not None:
            folders_to_download = util.listify( folders_to_download )

            current_user_roles = trans.get_current_user_roles()

            def traverse( folder ):
                admin = trans.user_is_admin()
                rval = []
                for subfolder in folder.active_folders:
                    if not admin:
                        can_access, folder_ids = trans.app.security_agent.check_folder_contents( trans.user, current_user_roles, subfolder )
                    if (admin or can_access) and not subfolder.deleted:
                        rval.extend( traverse( subfolder ) )
                for ld in folder.datasets:
                    if not admin:
                        can_access = trans.app.security_agent.can_access_dataset(
                            current_user_roles,
                            ld.library_dataset_dataset_association.dataset
                        )
                    if (admin or can_access) and not ld.deleted:
                        rval.append( ld )
                return rval

            for encoded_folder_id in folders_to_download:
                folder_id = self.folder_manager.cut_and_decode( trans, encoded_folder_id )
                folder = self.folder_manager.get( trans, folder_id )
                library_datasets.extend( traverse( folder ) )

        if not library_datasets:
            raise exceptions.RequestParameterMissingException( 'Request has to contain a list of dataset ids or folder ids to download.' )

        if format in [ 'zip', 'tgz', 'tbz' ]:
            # error = False
            killme = string.punctuation + string.whitespace
            trantab = string.maketrans( killme, '_' * len( killme ) )
            try:
                outext = 'zip'
                if format == 'zip':
                    # Can't use mkstemp - the file must not exist first
                    tmpd = tempfile.mkdtemp()
                    util.umask_fix_perms( tmpd, trans.app.config.umask, 0777, self.app.config.gid )
                    tmpf = os.path.join( tmpd, 'library_download.' + format )
                    if trans.app.config.upstream_gzip:
                        archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_STORED, True )
                    else:
                        archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_DEFLATED, True )
                    archive.add = lambda x, y: archive.write( x, y.encode( 'CP437' ) )
                elif format == 'tgz':
                    if trans.app.config.upstream_gzip:
                        archive = StreamBall( 'w|' )
                        outext = 'tar'
                    else:
                        archive = StreamBall( 'w|gz' )
                        outext = 'tgz'
                elif format == 'tbz':
                    archive = StreamBall( 'w|bz2' )
                    outext = 'tbz2'
            except ( OSError, zipfile.BadZipfile ):
                log.exception( "Unable to create archive for download" )
                raise exceptions.InternalServerError( "Unable to create archive for download." )
            except Exception:
                log.exception( "Unexpected error %s in create archive for download" % sys.exc_info()[ 0 ] )
                raise exceptions.InternalServerError( "Unable to create archive for download." )
            composite_extensions = trans.app.datatypes_registry.get_composite_extensions()
            seen = []
            for ld in library_datasets:
                ldda = ld.library_dataset_dataset_association
                ext = ldda.extension
                is_composite = ext in composite_extensions
                path = ""
                parent_folder = ldda.library_dataset.folder
                while parent_folder is not None:
                    # Exclude the now-hidden "root folder"
                    if parent_folder.parent is None:
                        path = os.path.join( parent_folder.library_root[ 0 ].name, path )
                        break
                    path = os.path.join( parent_folder.name, path )
                    parent_folder = parent_folder.parent
                path += ldda.name
                while path in seen:
                    path += '_'
                seen.append( path )
                zpath = os.path.split(path)[ -1 ]  # comes as base_name/fname
                outfname, zpathext = os.path.splitext( zpath )

                if is_composite:  # need to add all the components from the extra_files_path to the zip
                    if zpathext == '':
                        zpath = '%s.html' % zpath  # fake the real nature of the html file
                    try:
                        if format == 'zip':
                            archive.add( ldda.dataset.file_name, zpath )  # add the primary of a composite set
                        else:
                            archive.add( ldda.dataset.file_name, zpath, check_file=True )  # add the primary of a composite set
                    except IOError:
                        log.exception( "Unable to add composite parent %s to temporary library download archive" % ldda.dataset.file_name )
                        raise exceptions.InternalServerError( "Unable to create archive for download." )
                    except ObjectNotFound:
                        log.exception( "Requested dataset %s does not exist on the host." % ldda.dataset.file_name )
                        raise exceptions.ObjectNotFound( "Requested dataset not found. " )
                    except Exception as e:
                        log.exception( "Unable to add composite parent %s to temporary library download archive" % ldda.dataset.file_name )
                        raise exceptions.InternalServerError( "Unable to add composite parent to temporary library download archive. " + str( e ) )

                    flist = glob.glob(os.path.join(ldda.dataset.extra_files_path, '*.*'))  # glob returns full paths
                    for fpath in flist:
                        efp, fname = os.path.split(fpath)
                        if fname > '':
                            fname = fname.translate(trantab)
                        try:
                            if format == 'zip':
                                archive.add( fpath, fname )
                            else:
                                archive.add( fpath, fname, check_file=True )
                        except IOError:
                            log.exception( "Unable to add %s to temporary library download archive %s" % ( fname, outfname) )
                            raise exceptions.InternalServerError( "Unable to create archive for download." )
                        except ObjectNotFound:
                            log.exception( "Requested dataset %s does not exist on the host." % fpath )
                            raise exceptions.ObjectNotFound( "Requested dataset not found." )
                        except Exception as e:
                            log.exception( "Unable to add %s to temporary library download archive %s" % ( fname, outfname ) )
                            raise exceptions.InternalServerError( "Unable to add dataset to temporary library download archive . " + str( e ) )

                else:  # simple case
                    try:
                        if format == 'zip':
                            archive.add( ldda.dataset.file_name, path )
                        else:
                            archive.add( ldda.dataset.file_name, path, check_file=True )
                    except IOError:
                        log.exception( "Unable to write %s to temporary library download archive" % ldda.dataset.file_name )
                        raise exceptions.InternalServerError( "Unable to create archive for download" )
                    except ObjectNotFound:
                        log.exception( "Requested dataset %s does not exist on the host." % ldda.dataset.file_name )
                        raise exceptions.ObjectNotFound( "Requested dataset not found." )
                    except Exception as e:
                        log.exception( "Unable to add %s to temporary library download archive %s" % ( fname, outfname ) )
                        raise exceptions.InternalServerError( "Unknown error. " + str( e ) )
            lname = 'selected_dataset'
            fname = lname.replace( ' ', '_' ) + '_files'
            if format == 'zip':
                archive.close()
                trans.response.set_content_type( "application/octet-stream" )
                trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s.%s"' % ( fname, outext )
                archive = util.streamball.ZipBall( tmpf, tmpd )
                archive.wsgi_status = trans.response.wsgi_status()
                archive.wsgi_headeritems = trans.response.wsgi_headeritems()
                return archive.stream
            else:
                trans.response.set_content_type( "application/x-tar" )
                trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s.%s"' % ( fname, outext )
                archive.wsgi_status = trans.response.wsgi_status()
                archive.wsgi_headeritems = trans.response.wsgi_headeritems()
                return archive.stream
        elif format == 'uncompressed':
            if len(library_datasets) != 1:
                raise exceptions.RequestParameterInvalidException( "You can download only one uncompressed file at once." )
            else:
                single_ld = library_datasets[ 0 ]
                ldda = single_ld.library_dataset_dataset_association
                dataset = ldda.dataset
                fStat = os.stat( dataset.file_name )
                trans.response.set_content_type( ldda.get_mime() )
                trans.response.headers[ 'Content-Length' ] = int( fStat.st_size )
                fname = ldda.name
                fname = ''.join( c in util.FILENAME_VALID_CHARS and c or '_' for c in fname )[ 0:150 ]
                trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s"' % fname
                try:
                    return open( dataset.file_name )
                except:
                    raise exceptions.InternalServerError( "This dataset contains no content." )
        else:
            raise exceptions.RequestParameterInvalidException( "Wrong format parameter specified" )

    def _build_path( self, trans, folder ):
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
            path_to_root.extend( self._build_path( trans, upper_folder ) )
        return path_to_root

    def __decode_id( self, trans, encoded_id, object_name=None ):
        """
        Try to decode the id.

        :param  object_name:      Name of the object the id belongs to. (optional)
        :type   object_name:      str
        """
        try:
            return trans.security.decode_id( encoded_id )
        except TypeError:
            raise exceptions.MalformedId( 'Malformed %s id specified, unable to decode.' % object_name if object_name is not None else '' )
        except ValueError:
            raise exceptions.MalformedId( 'Wrong %s id specified, unable to decode.' % object_name if object_name is not None else '' )
