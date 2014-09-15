"""
API operations on library folders.
"""
from galaxy import util
from galaxy import web
from galaxy import exceptions
from galaxy.managers import folders
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import BaseAPIController, UsesLibraryMixin, UsesLibraryMixinItems
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound

import logging
log = logging.getLogger( __name__ )


class FoldersController( BaseAPIController, UsesLibraryMixin, UsesLibraryMixinItems ):

    def __init__( self, app ):
        super( FoldersController, self ).__init__( app )
        self.folder_manager = folders.FolderManager()

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        *GET /api/folders/
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

        :param  id:      the folder's encoded id (required)
        :type   id:      an encoded id string (has to be prefixed by 'F')

        :returns:   dictionary including details of the folder
        :rtype:     dict
        """
        folder_id = self.folder_manager.cut_and_decode( trans, id )
        folder = self.folder_manager.get( trans, folder_id, check_ownership=False, check_accessible=True )
        return_dict = self.folder_manager.get_folder_dict( trans, folder )
        return return_dict

    @expose_api
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

        :raises: RequestParameterMissingException
        """
        payload = kwd.get( 'payload', None )
        if payload is None:
            raise exceptions.RequestParameterMissingException( "Missing required parameter 'name'." )
        name = payload.get( 'name', None )
        if name is None:
            raise exceptions.RequestParameterMissingException( "Missing required parameter 'name'." )
        description = payload.get( 'description', '' )
        decoded_parent_folder_id = self.folder_manager.cut_and_decode( trans, encoded_parent_folder_id )
        parent_folder = self.folder_manager.get( trans, decoded_parent_folder_id )
        new_folder = self.folder_manager.create( trans, parent_folder.id, name, description )
        return self.folder_manager.get_folder_dict( trans, new_folder )
        
    @expose_api
    def get_permissions( self, trans, encoded_folder_id, **kwd ):
        """
        * GET /api/folders/{id}/permissions

        Load all permissions for the given folder id and return it.

        :param  encoded_folder_id:     the encoded id of the folder
        :type   encoded_folder_id:     an encoded id string

        :param  scope:      either 'current' or 'available'
        :type   scope:      string

        :returns:   dictionary with all applicable permissions' values
        :rtype:     dictionary

        :raises: ObjectNotFound, InsufficientPermissionsException
        """
        current_user_roles = trans.get_current_user_roles()
        is_admin = trans.user_is_admin()
        decoded_folder_id = self.folder_manager.cut_and_decode( trans, encoded_folder_id )
        folder = self.folder_manager.get( trans, decoded_folder_id )

        if not ( is_admin or trans.app.security_agent.can_manage_library_item( current_user_roles, folder ) ):
            raise exceptions.InsufficientPermissionsException( 'You do not have proper permission to access permissions of this folder.' )

        scope = kwd.get( 'scope', None )
        if scope == 'current' or scope is None:
            return self.folder_manager.get_current_roles( trans, folder )
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
            roles, total_roles = trans.app.security_agent.get_valid_roles( trans, folder, query, page, page_limit )
            return_roles = []
            for role in roles:
                role_id = trans.security.encode_id( role.id )
                return_roles.append( dict( id=role_id, name=role.name, type=role.type ) )
            return dict( roles=return_roles, page=page, page_limit=page_limit, total=total_roles )
        else:
            raise exceptions.RequestParameterInvalidException( "The value of 'scope' parameter is invalid. Alllowed values: current, available" )

    @expose_api
    def set_permissions( self, trans, encoded_folder_id, **kwd ):
        """
        def set_permissions( self, trans, encoded_folder_id, **kwd ):
            *POST /api/folders/{encoded_folder_id}/permissions

        :param  encoded_folder_id:      the encoded id of the folder to set the permissions of
        :type   encoded_folder_id:      an encoded id string      

        :param  action:     (required) describes what action should be performed
                            available actions: set_permissions
        :type   action:     string        

        :param  add_ids[]:         list of Role.id defining roles that should have add item permission on the folder
        :type   add_ids[]:         string or list  
        :param  manage_ids[]:      list of Role.id defining roles that should have manage permission on the folder
        :type   manage_ids[]:      string or list  
        :param  modify_ids[]:      list of Role.id defining roles that should have modify permission on the folder
        :type   modify_ids[]:      string or list          

        :rtype:     dictionary
        :returns:   dict of current roles for all available permission types.

        :raises: RequestParameterInvalidException, ObjectNotFound, InsufficientPermissionsException, InternalServerError
                    RequestParameterMissingException
        """
        is_admin = trans.user_is_admin()
        current_user_roles = trans.get_current_user_roles()

        decoded_folder_id = self.folder_manager.decode_folder_id( trans, self.folder_manager.cut_the_prefix( encoded_folder_id ) )
        folder = self.folder_manager.get( trans, decoded_folder_id )
        if not ( is_admin or trans.app.security_agent.can_manage_library_item( current_user_roles, folder ) ):
            raise exceptions.InsufficientPermissionsException( 'You do not have proper permission to modify permissions of this folder.' )

        new_add_roles_ids = util.listify( kwd.get( 'add_ids[]', None ) )
        new_manage_roles_ids = util.listify( kwd.get( 'manage_ids[]', None ) )
        new_modify_roles_ids = util.listify( kwd.get( 'modify_ids[]', None ) )

        action = kwd.get( 'action', None )
        if action is None:
            raise exceptions.RequestParameterMissingException( 'The mandatory parameter "action" is missing.' )
        elif action == 'set_permissions':

            # ADD TO LIBRARY ROLES
            valid_add_roles = []
            invalid_add_roles_names = []
            for role_id in new_add_roles_ids:
                role = self._load_role( trans, role_id )
                #  Check whether role is in the set of allowed roles
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles( trans, folder )
                if role in valid_roles:
                    valid_add_roles.append( role )
                else:
                    invalid_add_roles_names.append( role_id )
            if len( invalid_add_roles_names ) > 0:
                log.warning( "The following roles could not be added to the add library item permission: " + str( invalid_add_roles_names ) ) 
            
            # MANAGE FOLDER ROLES
            valid_manage_roles = []
            invalid_manage_roles_names = []
            for role_id in new_manage_roles_ids:
                role = self._load_role( trans, role_id )
                #  Check whether role is in the set of allowed roles
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles( trans, folder )
                if role in valid_roles:
                    valid_manage_roles.append( role )
                else:
                    invalid_manage_roles_names.append( role_id )
            if len( invalid_manage_roles_names ) > 0:
                log.warning( "The following roles could not be added to the manage folder permission: " + str( invalid_manage_roles_names ) ) 
            
            # MODIFY FOLDER ROLES
            valid_modify_roles = []
            invalid_modify_roles_names = []
            for role_id in new_modify_roles_ids:
                role = self._load_role( trans, role_id )
                #  Check whether role is in the set of allowed roles
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles( trans, folder )
                if role in valid_roles:
                    valid_modify_roles.append( role )
                else:
                    invalid_modify_roles_names.append( role_id )
            if len( invalid_modify_roles_names ) > 0:
                log.warning( "The following roles could not be added to the modify folder permission: " + str( invalid_modify_roles_names ) )                

            permissions = { trans.app.security_agent.permitted_actions.LIBRARY_ADD : valid_add_roles }
            permissions.update( { trans.app.security_agent.permitted_actions.LIBRARY_MANAGE : valid_manage_roles } )
            permissions.update( { trans.app.security_agent.permitted_actions.LIBRARY_MODIFY : valid_modify_roles } )

            trans.app.security_agent.set_all_library_permissions( trans, folder, permissions )
        else:
            raise exceptions.RequestParameterInvalidException( 'The mandatory parameter "action" has an invalid value.' 
                                'Allowed values are: "set_permissions"' )
        return self.folder_manager.get_current_roles( trans, folder )

    @web.expose_api
    def update( self, trans, id,  library_id, payload, **kwd ):
        """
        PUT /api/folders/{encoded_folder_id}

        """
        raise exceptions.NotImplemented( 'Updating folder through this endpoint is not implemented yet.' )

    # TODO move to Role manager
    def _load_role( self, trans, role_name ):
        """
        Method loads the role from the DB based on the given role name.

        :param  role_name:      name of the role to load from the DB
        :type   role_name:      string 

        :rtype:     Role
        :returns:   the loaded Role object

        :raises: InconsistentDatabase, RequestParameterInvalidException, InternalServerError
        """
        try:
            role = trans.sa_session.query( trans.app.model.Role ).filter( trans.model.Role.table.c.name == role_name ).one()
        except MultipleResultsFound:
            raise exceptions.InconsistentDatabase( 'Multiple roles found with the same name. Name: ' + str( role_name ) )
        except NoResultFound:
            raise exceptions.RequestParameterInvalidException( 'No role found with the name provided. Name: ' + str( role_name ) )
        except Exception, e:
            raise exceptions.InternalServerError( 'Error loading from the database.' + str(e))
        return role
