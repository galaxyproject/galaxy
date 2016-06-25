"""
API operations on Quota objects.
"""
import logging

from paste.httpexceptions import HTTPBadRequest
from sqlalchemy import false, true

from galaxy import web, util
from galaxy.actions.admin import AdminActions
from galaxy.exceptions import ActionInputError
from galaxy.web.base.controller import BaseAPIController, UsesQuotaMixin, url_for
from galaxy.web.base.controllers.admin import Admin
from galaxy.web.params import QuotaParamParser

log = logging.getLogger( __name__ )


class QuotaAPIController( BaseAPIController, Admin, AdminActions, UsesQuotaMixin, QuotaParamParser ):
    @web.expose_api
    @web.require_admin
    def index( self, trans, deleted='False', **kwd ):
        """
        GET /api/quotas
        GET /api/quotas/deleted
        Displays a collection (list) of quotas.
        """
        rval = []
        deleted = util.string_as_bool( deleted )
        query = trans.sa_session.query( trans.app.model.Quota )
        if deleted:
            route = 'deleted_quota'
            query = query.filter( trans.app.model.Quota.table.c.deleted == true() )
        else:
            route = 'quota'
            query = query.filter( trans.app.model.Quota.table.c.deleted == false() )
        for quota in query:
            item = quota.to_dict( value_mapper={ 'id': trans.security.encode_id } )
            encoded_id = trans.security.encode_id( quota.id )
            item['url'] = url_for( route, id=encoded_id )
            rval.append( item )
        return rval

    @web.expose_api
    @web.require_admin
    def show( self, trans, id, deleted='False', **kwd ):
        """
        GET /api/quotas/{encoded_quota_id}
        GET /api/quotas/deleted/{encoded_quota_id}
        Displays information about a quota.
        """
        quota = self.get_quota( trans, id, deleted=util.string_as_bool( deleted ) )
        return quota.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id, 'total_disk_usage': float } )

    @web.expose_api
    @web.require_admin
    def create( self, trans, payload, **kwd ):
        """
        POST /api/quotas
        Creates a new quota.
        """
        try:
            self.validate_in_users_and_groups( trans, payload )
        except Exception as e:
            raise HTTPBadRequest( detail=str( e ) )
        params = self.get_quota_params( payload )
        try:
            quota, message = self._create_quota( params )
        except ActionInputError as e:
            raise HTTPBadRequest( detail=str( e ) )
        item = quota.to_dict( value_mapper={ 'id': trans.security.encode_id } )
        item['url'] = url_for( 'quota', id=trans.security.encode_id( quota.id ) )
        item['message'] = message
        return item

    @web.expose_api
    @web.require_admin
    def update( self, trans, id, payload, **kwd ):
        """
        PUT /api/quotas/{encoded_quota_id}
        Modifies a quota.
        """
        try:
            self.validate_in_users_and_groups( trans, payload )
        except Exception as e:
            raise HTTPBadRequest( detail=str( e ) )

        quota = self.get_quota( trans, id, deleted=False )

        # FIXME: Doing it this way makes the update non-atomic if a method fails after an earlier one has succeeded.
        payload['id'] = id
        params = self.get_quota_params( payload )
        methods = []
        if payload.get( 'name', None ) or payload.get( 'description', None ):
            methods.append( self._rename_quota )
        if payload.get( 'amount', None ):
            methods.append( self._edit_quota )
        if payload.get( 'default', None ) == 'no':
            methods.append( self._unset_quota_default )
        elif payload.get( 'default', None ):
            methods.append( self._set_quota_default )
        if payload.get( 'in_users', None ) or payload.get( 'in_groups', None ):
            methods.append( self._manage_users_and_groups_for_quota )

        messages = []
        for method in methods:
            try:
                message = method( quota, params )
            except ActionInputError as e:
                raise HTTPBadRequest( detail=str( e ) )
            messages.append( message )
        return '; '.join( messages )

    @web.expose_api
    @web.require_admin
    def delete( self, trans, id, **kwd ):
        """
        DELETE /api/quotas/{encoded_quota_id}
        Deletes a quota
        """
        quota = self.get_quota( trans, id, deleted=False )  # deleted quotas are not technically members of this collection

        # a request body is optional here
        payload = kwd.get( 'payload', {} )
        payload['id'] = id
        params = self.get_quota_params( payload )

        try:
            message = self._mark_quota_deleted( quota, params )
            if util.string_as_bool( payload.get( 'purge', False ) ):
                message += self._purge_quota( quota, params )
        except ActionInputError as e:
            raise HTTPBadRequest( detail=str( e ) )
        return message

    @web.expose_api
    @web.require_admin
    def undelete( self, trans, id, **kwd ):
        """
        POST /api/quotas/deleted/{encoded_quota_id}/undelete
        Undeletes a quota
        """
        quota = self.get_quota( trans, id, deleted=True )
        try:
            return self._undelete_quota( quota )
        except ActionInputError as e:
            raise HTTPBadRequest( detail=str( e ) )
