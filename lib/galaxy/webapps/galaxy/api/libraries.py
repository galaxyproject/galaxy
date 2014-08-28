"""
API operations on a data library.
"""
from galaxy import util
from galaxy import exceptions
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.model.orm import and_, not_, or_
from galaxy.web.base.controller import BaseAPIController
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound

import logging
log = logging.getLogger( __name__ )


class LibrariesController( BaseAPIController ):

    @expose_api_anonymous
    def index( self, trans, **kwd ):
        """
        index( self, trans, **kwd )
        * GET /api/libraries:
            Returns a list of summary data for all libraries.

        :param  deleted: if True, show only ``deleted`` libraries, if False show only ``non-deleted``
        :type   deleted: boolean (optional)

        :returns:   list of dictionaries containing library information
        :rtype:     list

        .. seealso:: :attr:`galaxy.model.Library.dict_collection_visible_keys`

        """
        is_admin = trans.user_is_admin()
        query = trans.sa_session.query( trans.app.model.Library )
        deleted = kwd.get( 'deleted', 'missing' )
        try:
            if not is_admin:
                # non-admins can't see deleted libraries
                deleted = False
            else:
                deleted = util.asbool( deleted )
            if deleted:
                query = query.filter( trans.app.model.Library.table.c.deleted == True )
            else:
                query = query.filter( trans.app.model.Library.table.c.deleted == False )
        except ValueError:
            # given value wasn't true/false but the user is admin so we don't filter on this parameter at all
            pass

        if not is_admin:
            # non-admins can see only allowed and public libraries
            current_user_role_ids = [ role.id for role in trans.get_current_user_roles() ]
            library_access_action = trans.app.security_agent.permitted_actions.LIBRARY_ACCESS.action
            restricted_library_ids = [ lp.library_id for lp in ( trans.sa_session.query( trans.model.LibraryPermissions )
                                                                 .filter( trans.model.LibraryPermissions.table.c.action == library_access_action )
                                                                 .distinct() ) ]
            accessible_restricted_library_ids = [ lp.library_id for lp in ( trans.sa_session.query( trans.model.LibraryPermissions )
                                                  .filter( and_( trans.model.LibraryPermissions.table.c.action == library_access_action,
                                                                 trans.model.LibraryPermissions.table.c.role_id.in_( current_user_role_ids ) ) ) ) ]
            query = query.filter( or_( not_( trans.model.Library.table.c.id.in_( restricted_library_ids ) ), trans.model.Library.table.c.id.in_( accessible_restricted_library_ids ) ) )
        libraries = []
        for library in query:
            item = library.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id, 'root_folder_id': trans.security.encode_id } )
            if trans.app.security_agent.library_is_public( library, contents=False ):
                item[ 'public' ] = True
            current_user_roles = trans.get_current_user_roles()
            if not trans.user_is_admin():
                item['can_user_add'] = trans.app.security_agent.can_add_library_item( current_user_roles, library )
                item['can_user_modify'] = trans.app.security_agent.can_modify_library_item( current_user_roles, library )
                item['can_user_manage'] = trans.app.security_agent.can_manage_library_item( current_user_roles, library )
            else:
                item['can_user_add'] = True
                item['can_user_modify'] = True
                item['can_user_manage'] = True
            libraries.append( item )
        return libraries

    @expose_api_anonymous
    def show( self, trans, id, deleted='False', **kwd ):
        """
        show( self, trans, id, deleted='False', **kwd )
        * GET /api/libraries/{encoded_id}:
            returns detailed information about a library
        * GET /api/libraries/deleted/{encoded_id}:
            returns detailed information about a ``deleted`` library

        :param  id:      the encoded id of the library
        :type   id:      an encoded id string
        :param  deleted: if True, allow information on a ``deleted`` library
        :type   deleted: boolean

        :returns:   detailed library information
        :rtype:     dictionary

        .. seealso:: :attr:`galaxy.model.Library.dict_element_visible_keys`

        :raises: MalformedId, ObjectNotFound
        """
        library_id = id
        deleted = util.string_as_bool( deleted )
        library = self._load_library( trans, library_id, deleted )
        if not library or not ( trans.user_is_admin() or trans.app.security_agent.can_access_library( trans.get_current_user_roles(), library ) ):
            raise exceptions.ObjectNotFound( 'Library with the id provided ( %s ) was not found' % id )
        return library.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id, 'root_folder_id': trans.security.encode_id } )

    def _load_library( self, trans, encoded_library_id, deleted=False ):
        try:
            decoded_library_id = trans.security.decode_id( encoded_library_id )
        except TypeError:
            raise exceptions.MalformedId( 'Malformed library id ( %s ) specified, unable to decode.' % id )
        try:
            library = trans.sa_session.query( trans.app.model.Library ).get( decoded_library_id )
            assert library.deleted == deleted
        except Exception:
            library = None
        return library

    @expose_api
    def create( self, trans, payload, **kwd ):
        """
        create( self, trans, payload, **kwd )
        * POST /api/libraries:
            Creates a new library. Only ``name`` parameter is required.

        .. note:: Currently, only admin users can create libraries.

        :param  payload: dictionary structure containing::
            'name':         the new library's name (required)
            'description':  the new library's description (optional)
            'synopsis':     the new library's synopsis (optional)
        :type   payload: dict

        :returns:   detailed library information
        :rtype:     dict

        :raises: ItemAccessibilityException, RequestParameterMissingException
        """
        if not trans.user_is_admin():
            raise exceptions.ItemAccessibilityException( 'Only administrators can create libraries.' )
        params = util.Params( payload )
        name = util.restore_text( params.get( 'name', None ) )
        if not name:
            raise exceptions.RequestParameterMissingException( "Missing required parameter 'name'." )
        description = util.restore_text( params.get( 'description', '' ) )
        synopsis = util.restore_text( params.get( 'synopsis', '' ) )
        if synopsis in [ 'None', None ]:
            synopsis = ''
        library = trans.app.model.Library( name=name, description=description, synopsis=synopsis )
        root_folder = trans.app.model.LibraryFolder( name=name, description='' )
        library.root_folder = root_folder
        trans.sa_session.add_all( ( library, root_folder ) )
        trans.sa_session.flush()

        item = library.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id, 'root_folder_id': trans.security.encode_id } )
        item['can_user_add'] = True
        item['can_user_modify'] = True
        item['can_user_manage'] = True
        if trans.app.security_agent.library_is_public( library, contents=False ):
            item[ 'public' ] = True
        return item

    @expose_api
    def update( self, trans, id, **kwd ):
        """
        * PATCH /api/libraries/{encoded_id}
           Updates the library defined by an ``encoded_id`` with the data in the payload.

       .. note:: Currently, only admin users can update libraries. Also the library must not be `deleted`.

        :param  id:      the encoded id of the library
        :type   id:      an encoded id string

        :param  payload: (required) dictionary structure containing::
            'name':         new library's name, cannot be empty
            'description':  new library's description
            'synopsis':     new library's synopsis
        :type   payload: dict

        :returns:   detailed library information
        :rtype:     dict

        :raises: ItemAccessibilityException, MalformedId, ObjectNotFound, RequestParameterInvalidException, RequestParameterMissingException
        """
        if not trans.user_is_admin():
            raise exceptions.ItemAccessibilityException( 'Only administrators can update libraries.' )

        try:
            decoded_id = trans.security.decode_id( id )
        except Exception:
            raise exceptions.MalformedId( 'Malformed library id ( %s ) specified, unable to decode.' % id )
        library = None
        try:
            library = trans.sa_session.query( trans.app.model.Library ).get( decoded_id )
        except Exception:
            library = None
        if not library:
            raise exceptions.ObjectNotFound( 'Library with the id provided ( %s ) was not found' % id )
        if library.deleted:
            raise exceptions.RequestParameterInvalidException( 'You cannot modify a deleted library. Undelete it first.' )
        payload = kwd.get( 'payload', None )
        if payload:
            name = payload.get( 'name', None )
            if name == '':
                raise exceptions.RequestParameterMissingException( "Parameter 'name' of library is required. You cannot remove it." )
            library.name = name
            if payload.get( 'description', None ) or payload.get( 'description', None ) == '':
                library.description = payload.get( 'description', None )
            if payload.get( 'synopsis', None ) or payload.get( 'synopsis', None ) == '':
                library.synopsis = payload.get( 'synopsis', None )
        else:
            raise exceptions.RequestParameterMissingException( "You did not specify any payload." )
        trans.sa_session.add( library )
        trans.sa_session.flush()
        return library.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id, 'root_folder_id': trans.security.encode_id } )

    @expose_api
    def delete( self, trans, id, **kwd ):
        """
        delete( self, trans, id, **kwd )
        * DELETE /api/libraries/{id}
            marks the library with the given ``id`` as `deleted` (or removes the `deleted` mark if the `undelete` param is true)

        .. note:: Currently, only admin users can un/delete libraries.

        :param  id:     the encoded id of the library to un/delete
        :type   id:     an encoded id string

        :param  undelete:    (optional) flag specifying whether the item should be deleted or undeleted, defaults to false:
        :type   undelete:    bool

        :returns:   detailed library information
        :rtype:     dictionary

        .. seealso:: :attr:`galaxy.model.Library.dict_element_visible_keys`

        :raises: ItemAccessibilityException, MalformedId, ObjectNotFound
        """
        undelete = util.string_as_bool( kwd.get( 'undelete', False ) )
        if not trans.user_is_admin():
            raise exceptions.ItemAccessibilityException( 'Only administrators can delete and undelete libraries.' )
        try:
            decoded_id = trans.security.decode_id( id )
        except Exception:
            raise exceptions.MalformedId( 'Malformed library id ( %s ) specified, unable to decode.' % id )
        try:
            library = trans.sa_session.query( trans.app.model.Library ).get( decoded_id )
        except Exception:
            library = None
        if not library:
            raise exceptions.ObjectNotFound( 'Library with the id provided ( %s ) was not found' % id )

        if undelete:
            library.deleted = False
        else:
            library.deleted = True

        trans.sa_session.add( library )
        trans.sa_session.flush()
        return library.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id, 'root_folder_id': trans.security.encode_id } )

    @expose_api
    def get_permissions( self, trans, encoded_library_id, **kwd ):
        """
        * GET /api/libraries/{id}/permissions

        Load all permissions for the given library id and return it.

        :param  encoded_library_id:     the encoded id of the library
        :type   encoded_library_id:     an encoded id string

        :param  scope:      either 'current' or 'available'
        :type   scope:      string

        :param  is_library_access:      indicates whether the roles available for the library access are requested
        :type   is_library_access:      bool

        :returns:   dictionary with all applicable permissions' values
        :rtype:     dictionary

        :raises: ObjectNotFound, InsufficientPermissionsException
        """
        current_user_roles = trans.get_current_user_roles()
        is_admin = trans.user_is_admin()
        library = self._load_library( trans, encoded_library_id )
        if not library or not ( is_admin or trans.app.security_agent.can_access_library( current_user_roles, library ) ):
            raise exceptions.ObjectNotFound( 'Library with the id provided ( %s ) was not found' % id )
        if not ( is_admin or trans.app.security_agent.can_manage_library_item( current_user_roles, library ) ):
            raise exceptions.InsufficientPermissionsException( 'You do not have proper permission to access permissions of this library.' )

        scope = kwd.get( 'scope', None )
        is_library_access = util.string_as_bool( kwd.get( 'is_library_access', False ) )

        if scope == 'current' or scope is None:
            return self._get_current_roles( trans, library )

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

            roles, total_roles = trans.app.security_agent.get_valid_roles( trans, library, query, page, page_limit, is_library_access )

            return_roles = []
            for role in roles:
                return_roles.append( dict( id=role.name, name=role.name, type=role.type ) )
            return dict( roles=return_roles, page=page, page_limit=page_limit, total=total_roles )
        else:
            raise exceptions.RequestParameterInvalidException( "The value of 'scope' parameter is invalid. Alllowed values: current, available" )

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


    @expose_api
    def set_permissions( self, trans, encoded_library_id, **kwd ):
        """
        def set_permissions( self, trans, encoded_dataset_id, **kwd ):
            *POST /api/libraries/{encoded_library_id}/permissions

        :param  encoded_library_id:      the encoded id of the library to set the permissions of
        :type   encoded_library_id:      an encoded id string      

        :param  action:     (required) describes what action should be performed
                            available actions: remove_restrictions, set_permissions
        :type   action:     string        

        :param  access_ids[]:      list of Role.name defining roles that should have access permission on the library
        :type   access_ids[]:      string or list  
        :param  add_ids[]:         list of Role.name defining roles that should have add item permission on the library
        :type   add_ids[]:         string or list  
        :param  manage_ids[]:      list of Role.name defining roles that should have manage permission on the library
        :type   manage_ids[]:      string or list  
        :param  modify_ids[]:      list of Role.name defining roles that should have modify permission on the library
        :type   modify_ids[]:      string or list          

        :rtype:     dictionary
        :returns:   dict of current roles for all available permission types

        :raises: RequestParameterInvalidException, ObjectNotFound, InsufficientPermissionsException, InternalServerError
                    RequestParameterMissingException
        """
        is_admin = trans.user_is_admin()
        current_user_roles = trans.get_current_user_roles()
        library = self._load_library( trans, encoded_library_id )
        if not library or not ( is_admin or trans.app.security_agent.can_access_library( current_user_roles, library ) ):
            raise exceptions.ObjectNotFound( 'Library with the id provided ( %s ) was not found' % id )
        if not ( is_admin or trans.app.security_agent.can_manage_library_item( current_user_roles, library ) ):
            raise exceptions.InsufficientPermissionsException( 'You do not have proper permission to modify permissions of this library.' )

        new_access_roles_ids = util.listify( kwd.get( 'access_ids[]', None ) )
        new_add_roles_ids = util.listify( kwd.get( 'add_ids[]', None ) )
        new_manage_roles_ids = util.listify( kwd.get( 'manage_ids[]', None ) )
        new_modify_roles_ids = util.listify( kwd.get( 'modify_ids[]', None ) )

        action = kwd.get( 'action', None )
        if action is None:
            payload = kwd.get( 'payload', None )
            if payload is not None:
                return self.set_permissions_old( trans, library, payload, **kwd )
            else:
                raise exceptions.RequestParameterMissingException( 'The mandatory parameter "action" is missing.' )
        elif action == 'remove_restrictions':
            trans.app.security_agent.make_library_public( library )
            if not trans.app.security_agent.library_is_public( library ):
                raise exceptions.InternalServerError( 'An error occured while making library public.' )
        elif action == 'set_permissions':

            # ACCESS LIBRARY ROLES
            valid_access_roles = []
            invalid_access_roles_names = []
            for role_id in new_access_roles_ids:
                role = self._load_role( trans, role_id )
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles( trans, library, is_library_access=True )
                if role in valid_roles:
                    valid_access_roles.append( role )
                else:
                    invalid_access_roles_names.append( role_id )
            if len( invalid_access_roles_names ) > 0:
                log.warning( "The following roles could not be added to the library access permission: " + str( invalid_access_roles_names ) )                

            # ADD TO LIBRARY ROLES
            valid_add_roles = []
            invalid_add_roles_names = []
            for role_id in new_add_roles_ids:
                role = self._load_role( trans, role_id )
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles( trans, library )
                if role in valid_roles:
                    valid_add_roles.append( role )
                else:
                    invalid_add_roles_names.append( role_id )
            if len( invalid_add_roles_names ) > 0:
                log.warning( "The following roles could not be added to the add library item permission: " + str( invalid_add_roles_names ) ) 
            
            # MANAGE LIBRARY ROLES
            valid_manage_roles = []
            invalid_manage_roles_names = []
            for role_id in new_manage_roles_ids:
                role = self._load_role( trans, role_id )
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles( trans, library )
                if role in valid_roles:
                    valid_manage_roles.append( role )
                else:
                    invalid_manage_roles_names.append( role_id )
            if len( invalid_manage_roles_names ) > 0:
                log.warning( "The following roles could not be added to the manage library permission: " + str( invalid_manage_roles_names ) ) 
            
            # MODIFY LIBRARY ROLES
            valid_modify_roles = []
            invalid_modify_roles_names = []
            for role_id in new_modify_roles_ids:
                role = self._load_role( trans, role_id )
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles( trans, library )
                if role in valid_roles:
                    valid_modify_roles.append( role )
                else:
                    invalid_modify_roles_names.append( role_id )
            if len( invalid_modify_roles_names ) > 0:
                log.warning( "The following roles could not be added to the modify library permission: " + str( invalid_modify_roles_names ) )                

            permissions = { trans.app.security_agent.permitted_actions.LIBRARY_ACCESS : valid_access_roles }
            permissions.update( { trans.app.security_agent.permitted_actions.LIBRARY_ADD : valid_add_roles } )
            permissions.update( { trans.app.security_agent.permitted_actions.LIBRARY_MANAGE : valid_manage_roles } )
            permissions.update( { trans.app.security_agent.permitted_actions.LIBRARY_MODIFY : valid_modify_roles } )

            trans.app.security_agent.set_all_library_permissions( trans, library, permissions )
            trans.sa_session.refresh( library )
            # Copy the permissions to the root folder
            trans.app.security_agent.copy_library_permissions( trans, library, library.root_folder )
        else:
            raise exceptions.RequestParameterInvalidException( 'The mandatory parameter "action" has an invalid value.' 
                                'Allowed values are: "remove_restrictions", set_permissions"' )

        return self._get_current_roles( trans, library )


    def _get_current_roles( self, trans, library):
        """
        Find all roles currently connected to relevant permissions 
        on the library.

        :param  library:      the model object
        :type   library:      Library

        :rtype:     dictionary
        :returns:   dict of current roles for all available permission types
        """
        # Omit duplicated roles by converting to set 
        access_roles = set( library.get_access_roles( trans ) )
        modify_roles = set( trans.app.security_agent.get_roles_for_action( library, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY ) )
        manage_roles = set( trans.app.security_agent.get_roles_for_action( library, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE ) )
        add_roles = set( trans.app.security_agent.get_roles_for_action( library, trans.app.security_agent.permitted_actions.LIBRARY_ADD ) )

        access_library_role_list = [ access_role.name for access_role in access_roles ]
        modify_library_role_list = [ modify_role.name for modify_role in modify_roles ]
        manage_library_role_list = [ manage_role.name for manage_role in manage_roles ]
        add_library_item_role_list = [ add_role.name for add_role in add_roles ]

        return dict( access_library_role_list=access_library_role_list, modify_library_role_list=modify_library_role_list, manage_library_role_list=manage_library_role_list, add_library_item_role_list=add_library_item_role_list )


    def set_permissions_old( self, trans, library, payload, **kwd ):
        """
        *** old implementation for backward compatibility ***

        POST /api/libraries/{encoded_library_id}/permissions
        Updates the library permissions.
        """
        params = galaxy.util.Params( payload )
        permissions = {}
        for k, v in trans.app.model.Library.permitted_actions.items():
            role_params = params.get( k + '_in', [] )
            in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( trans.security.decode_id( x ) ) for x in galaxy.util.listify( role_params ) ]
            permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
        trans.app.security_agent.set_all_library_permissions( trans, library, permissions )
        trans.sa_session.refresh( library )
        # Copy the permissions to the root folder
        trans.app.security_agent.copy_library_permissions( trans, library, library.root_folder )
        message = "Permissions updated for library '%s'." % library.name

        item = library.to_dict( view='element', value_mapper={ 'id' : trans.security.encode_id , 'root_folder_id' : trans.security.encode_id } )
        return item

