"""
API operations on a data library.
"""
from galaxy import util
from galaxy import exceptions
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.model.orm import and_, not_, or_
from galaxy.web.base.controller import BaseAPIController

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
        query = trans.sa_session.query( trans.app.model.Library )
        deleted = kwd.get( 'deleted', 'missing' )
        try:
            if not trans.user_is_admin():
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
        try:
            decoded_library_id = trans.security.decode_id( library_id )
        except TypeError:
            raise exceptions.MalformedId( 'Malformed library id ( %s ) specified, unable to decode.' % id )
        try:
            library = trans.sa_session.query( trans.app.model.Library ).get( decoded_library_id )
            assert library.deleted == deleted
        except Exception:
            library = None
        if not library or not ( trans.user_is_admin() or trans.app.security_agent.can_access_library( trans.get_current_user_roles(), library ) ):
            raise exceptions.ObjectNotFound( 'Library with the id provided ( %s ) was not found' % id )
        return library.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id, 'root_folder_id': trans.security.encode_id } )

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
