"""
API operations on Group objects.
"""
import logging
from galaxy.web.base.controller import BaseAPIController, url_for
from galaxy import web

log = logging.getLogger( __name__ )


class GroupUsersAPIController( BaseAPIController ):

    @web.expose_api
    @web.require_admin
    def index( self, trans, group_id, **kwd ):
        """
        GET /api/groups/{encoded_group_id}/users
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
            for uga in group.users:
                user = uga.user
                encoded_id = trans.security.encode_id( user.id )
                rval.append( dict( id=encoded_id,
                                   email=user.email,
                                   url=url_for( 'group_user', group_id=group_id, id=encoded_id, ) ) )
        except Exception as e:
            rval = "Error in group API at listing users"
            log.error( rval + ": %s" % str(e) )
            trans.response.status = 500
        return rval

    @web.expose_api
    @web.require_admin
    def show( self, trans, id, group_id, **kwd ):
        """
        GET /api/groups/{encoded_group_id}/users/{encoded_user_id}
        Displays information about a group user.
        """
        user_id = id
        decoded_group_id = trans.security.decode_id( group_id )
        decoded_user_id = trans.security.decode_id( user_id )
        item = None
        try:
            group = trans.sa_session.query( trans.app.model.Group ).get( decoded_group_id )
            user = trans.sa_session.query( trans.app.model.User ).get( decoded_user_id )
            for uga in group.users:
                if uga.user == user:
                    item = dict( id=user_id,
                                 email=user.email,
                                 url=url_for( 'group_user', group_id=group_id, id=user_id) )  # TODO Fix This
            if not item:
                item = "user %s not in group %s" % (user.email, group.name)
        except Exception as e:
            item = "Error in group_user API group %s user %s" % (group.name, user.email)
            log.error(item + ": %s" % str(e))
        return item

    @web.expose_api
    @web.require_admin
    def update( self, trans, id, group_id, **kwd ):
        """
        PUT /api/groups/{encoded_group_id}/users/{encoded_user_id}
        Adds a user to a group
        """
        user_id = id
        decoded_group_id = trans.security.decode_id( group_id )
        decoded_user_id = trans.security.decode_id( user_id )
        item = None
        try:
            group = trans.sa_session.query( trans.app.model.Group ).get( decoded_group_id )
            user = trans.sa_session.query( trans.app.model.User ).get( decoded_user_id )
            for uga in group.users:
                if uga.user == user:
                    item = dict( id=user_id,
                                 email=user.email,
                                 url=url_for( 'group_user', group_id=group_id, id=user_id) )
            if not item:
                uga = trans.app.model.UserGroupAssociation( user, group )
                # Add UserGroupAssociations
                trans.sa_session.add( uga )
                trans.sa_session.flush()
                item = dict( id=user_id,
                             email=user.email,
                             url=url_for( 'group_user', group_id=group_id, id=user_id) )
        except Exception as e:
            item = "Error in group_user API Adding user %s to group %s" % (user.email, group.name)
            log.error(item + ": %s" % str(e))
        return item

    @web.expose_api
    @web.require_admin
    def delete( self, trans, id, group_id, **kwd ):
        """
        DELETE /api/groups/{encoded_group_id}/users/{encoded_user_id}
        Removes a user from a group
        """
        user_id = id
        decoded_group_id = trans.security.decode_id( group_id )
        decoded_user_id = trans.security.decode_id( user_id )
        try:
            group = trans.sa_session.query( trans.app.model.Group ).get( decoded_group_id )
            user = trans.sa_session.query( trans.app.model.User ).get( decoded_user_id )
            for uga in group.users:
                if uga.user == user:
                    trans.sa_session.delete( uga )
                    trans.sa_session.flush()
                    item = dict( id=user_id,
                                 email=user.email,
                                 url=url_for( 'group_user', group_id=group_id, id=user_id) )
            if not item:
                item = "user %s not in group %s" % (user.email, group.name)
        except Exception as e:
            item = "Error in group_user API Removing user %s from group %s" % (user.email, group.name)
            log.error(item + ": %s" % str(e))
        return item
