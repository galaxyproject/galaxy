"""
API operations on Group objects.
"""
import logging
from galaxy.web.base.controller import BaseAPIController, url_for
from galaxy import web

log = logging.getLogger( __name__ )


class GroupRolesAPIController( BaseAPIController ):

    @web.expose_api
    @web.require_admin
    def index( self, trans, group_id, **kwd ):
        """
        GET /api/groups/{encoded_group_id}/roles
        Displays a collection (list) of groups.
        """
        decoded_group_id = trans.security.decode_id( group_id )
        try:
            group = trans.sa_session.query( trans.app.model.Group ).get( decoded_group_id )
        except:
            group = None
        if not group:
            trans.response.status = 400
            return "Invalid group id ( %s ) specified." % str( group_id )
        rval = []
        try:
            for gra in group.roles:
                role = gra.role
                encoded_id = trans.security.encode_id( role.id )
                rval.append( dict( id=encoded_id,
                                   name=role.name,
                                   url=url_for( 'group_role', group_id=group_id, id=encoded_id, ) ) )
        except Exception as e:
            rval = "Error in group API at listing roles"
            log.error( rval + ": %s" % str(e) )
            trans.response.status = 500
        return rval

    @web.expose_api
    @web.require_admin
    def show( self, trans, id, group_id, **kwd ):
        """
        GET /api/groups/{encoded_group_id}/roles/{encoded_role_id}
        Displays information about a group role.
        """
        role_id = id
        decoded_group_id = trans.security.decode_id( group_id )
        decoded_role_id = trans.security.decode_id( role_id )
        item = None
        try:
            group = trans.sa_session.query( trans.app.model.Group ).get( decoded_group_id )
            role = trans.sa_session.query( trans.app.model.Role ).get( decoded_role_id )
            for gra in group.roles:
                if gra.role == role:
                    item = dict( id=role_id,
                                 name=role.name,
                                 url=url_for( 'group_role', group_id=group_id, id=role_id) )  # TODO Fix This
            if not item:
                item = "role %s not in group %s" % (role.name, group.name)
        except Exception as e:
            item = "Error in group_role API group %s role %s" % (group.name, role.name)
            log.error(item + ": %s" % str(e))
        return item

    @web.expose_api
    @web.require_admin
    def update( self, trans, id, group_id, **kwd ):
        """
        PUT /api/groups/{encoded_group_id}/roles/{encoded_role_id}
        Adds a role to a group
        """
        role_id = id
        decoded_group_id = trans.security.decode_id( group_id )
        decoded_role_id = trans.security.decode_id( role_id )
        item = None
        try:
            group = trans.sa_session.query( trans.app.model.Group ).get( decoded_group_id )
            role = trans.sa_session.query( trans.app.model.Role ).get( decoded_role_id )
            for gra in group.roles:
                if gra.role == role:
                    item = dict( id=role_id,
                                 name=role.name,
                                 url=url_for( 'group_role', group_id=group_id, id=role_id) )
            if not item:
                gra = trans.app.model.GroupRoleAssociation( group, role )
                # Add GroupRoleAssociation
                trans.sa_session.add( gra )
                trans.sa_session.flush()
                item = dict( id=role_id,
                             name=role.name,
                             url=url_for( 'group_role', group_id=group_id, id=role_id) )
        except Exception as e:
            item = "Error in group_role API Adding role %s to group %s" % (role.name, group.name)
            log.error(item + ": %s" % str(e))
        return item

    @web.expose_api
    @web.require_admin
    def delete( self, trans, id, group_id, **kwd ):
        """
        DELETE /api/groups/{encoded_group_id}/roles/{encoded_role_id}
        Removes a role from a group
        """
        role_id = id
        decoded_group_id = trans.security.decode_id( group_id )
        decoded_role_id = trans.security.decode_id( role_id )
        try:
            group = trans.sa_session.query( trans.app.model.Group ).get( decoded_group_id )
            role = trans.sa_session.query( trans.app.model.Role ).get( decoded_role_id )
            for gra in group.roles:
                if gra.role == role:
                    trans.sa_session.delete( gra )
                    trans.sa_session.flush()
                    item = dict( id=role_id,
                                 name=role.name,
                                 url=url_for( 'group_role', group_id=group_id, id=role_id) )
            if not item:
                item = "role %s not in group %s" % (role.name, group.name)
        except Exception as e:
            item = "Error in group_role API Removing role %s from group %s" % (role.name, group.name)
            log.error(item + ": %s" % str(e))
        return item
