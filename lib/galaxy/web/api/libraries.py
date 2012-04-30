"""
API operations on a library.
"""
import logging, os, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.orm import *
from paste.httpexceptions import *

log = logging.getLogger( __name__ )

class LibrariesController( BaseAPIController ):
    
    @web.expose_api
    def index( self, trans, deleted='False', **kwd ):
        """
        GET /api/libraries
        GET /api/libraries/deleted
        Displays a collection (list) of libraries.
        """
        query = trans.sa_session.query( trans.app.model.Library )
        deleted = util.string_as_bool( deleted )
        if deleted:
            route = 'deleted_library'
            query = query.filter( trans.app.model.Library.table.c.deleted == True )
        else:
            route = 'library'
            query = query.filter( trans.app.model.Library.table.c.deleted == False )
        current_user_role_ids = [ role.id for role in trans.get_current_user_roles() ]
        library_access_action = trans.app.security_agent.permitted_actions.LIBRARY_ACCESS.action
        restricted_library_ids = [ lp.library_id for lp in trans.sa_session.query( trans.model.LibraryPermissions ) \
                                                                           .filter( trans.model.LibraryPermissions.table.c.action == library_access_action ) \
                                                                           .distinct() ]
        accessible_restricted_library_ids = [ lp.library_id for lp in trans.sa_session.query( trans.model.LibraryPermissions ) \
                                                                                      .filter( and_( trans.model.LibraryPermissions.table.c.action == library_access_action,
                                                                                                     trans.model.LibraryPermissions.table.c.role_id.in_( current_user_role_ids ) ) ) ]
        query = query.filter( or_( not_( trans.model.Library.table.c.id.in_( restricted_library_ids ) ),
                           trans.model.Library.table.c.id.in_( accessible_restricted_library_ids ) ) )
        rval = []
        for library in query:
            item = library.get_api_value()
            item['url'] = url_for( route, id=trans.security.encode_id( library.id ) )
            item['id'] = trans.security.encode_id( item['id'] )
            rval.append( item )
        return rval

    @web.expose_api
    def show( self, trans, id, deleted='False', **kwd ):
        """
        GET /api/libraries/{encoded_library_id}
        GET /api/libraries/deleted/{encoded_library_id}
        Displays information about a library.
        """
        library_id = id
        deleted = util.string_as_bool( deleted )
        params = util.Params( kwd )
        try:
            decoded_library_id = trans.security.decode_id( library_id )
        except TypeError:
            raise HTTPBadRequest( detail='Malformed library id ( %s ) specified, unable to decode.' % id )
        try:
            library = trans.sa_session.query( trans.app.model.Library ).get( decoded_library_id )
            assert library.deleted == deleted
        except:
            library = None
        if not library or not ( trans.user_is_admin() or trans.app.security_agent.can_access_library( trans.get_current_user_roles(), library ) ):
            raise HTTPBadRequest( detail='Invalid library id ( %s ) specified.' % id )
        item = library.get_api_value( view='element' )
        #item['contents_url'] = url_for( 'contents', library_id=library_id )
        item['contents_url'] = url_for( 'library_contents', library_id=library_id )
        return item

    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/libraries
        Creates a new library.
        """
        if not trans.user_is_admin():
            raise HTTPForbidden( detail='You are not authorized to create a new library.' )
        params = util.Params( payload )
        name = util.restore_text( params.get( 'name', None ) )
        if not name:
            raise HTTPBadRequest( detail="Missing required parameter 'name'." )
        description = util.restore_text( params.get( 'description', '' ) )
        synopsis = util.restore_text( params.get( 'synopsis', '' ) )
        if synopsis in [ 'None', None ]:
            synopsis = ''
        library = trans.app.model.Library( name=name, description=description, synopsis=synopsis )
        root_folder = trans.app.model.LibraryFolder( name=name, description='' )
        library.root_folder = root_folder
        trans.sa_session.add_all( ( library, root_folder ) )
        trans.sa_session.flush()
        encoded_id = trans.security.encode_id( library.id )
        rval = {}
        rval['url'] = url_for( 'library', id=encoded_id )
        rval['name'] = name
        rval['id'] = encoded_id
        return [ rval ]

    @web.expose_api
    def delete( self, trans, id, **kwd ):
        if not trans.user_is_admin():
            raise HTTPForbidden( detail='You are not authorized to delete libraries.' )
        try:
            decoded_id = trans.security.decode_id( id )
        except TypeError:
            raise HTTPBadRequest( detail='Malformed library id ( %s ) specified, unable to decode.' % id )
        try:
            library = trans.sa_session.query( trans.app.model.Library ).get( decoded_id )
        except:
            library = None
        if not library:
            raise HTTPBadRequest( detail='Invalid library id ( %s ) specified.' % id )
        library.deleted = True
        trans.sa_session.add( library )
        trans.sa_session.flush()
        return library.get_api_value( view='element', value_mapper={ 'id' : trans.security.encode_id } )
