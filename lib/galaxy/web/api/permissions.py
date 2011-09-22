"""
API operations on the permissions of a library.
"""
import logging, os, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.orm import *

log = logging.getLogger( __name__ )

class PermissionsController( BaseAPIController ):
    
    # Method not ideally named
    @web.expose_api
    def create( self, trans, library_id, payload, **kwd ): 
        """
        POST /api/libraries/{encoded_library_id}/permissions
        Updates the library permissions.
        """
        if not trans.user_is_admin():
            trans.response.status = 403
            return "You are not authorized to update library permissions."

        params = util.Params( payload )
        try:
            decoded_library_id = trans.security.decode_id( library_id )
        except TypeError:
            trans.response.status = 400
            return "Malformed library id ( %s ) specified, unable to decode." % str( library_id )

        try:
            library = trans.sa_session.query( trans.app.model.Library ).get( decoded_library_id )
        except:
            library = None

        permissions = {}
        for k, v in trans.app.model.Library.permitted_actions.items():
            role_params = params.get( k + '_in', [] )
            in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( trans.security.decode_id( x ) ) for x in util.listify( role_params ) ]
            permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
        trans.app.security_agent.set_all_library_permissions( library, permissions )
        trans.sa_session.refresh( library )
        # Copy the permissions to the root folder
        trans.app.security_agent.copy_library_permissions( library, library.root_folder )
        message = "Permissions updated for library '%s'." % library.name

        item = library.get_api_value( view='element' )
        return item

