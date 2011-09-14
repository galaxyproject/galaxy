"""
API operations on Quota objects.
"""
import logging
from galaxy.web.base.controller import BaseController, url_for
from galaxy import web, util
from elementtree.ElementTree import XML
from galaxy.web.api.util import *

log = logging.getLogger( __name__ )

class QuotaAPIController( BaseController ):
    @web.expose_api
    @web.require_admin
    def index( self, trans, deleted=False, **kwd ):
        """
        GET /api/quotas
        GET /api/quotas/deleted
        Displays a collection (list) of quotas.
        """
        #return str( trans.webapp.api_mapper )
        rval = []
        query = trans.sa_session.query( trans.app.model.Quota )
        if deleted:
            route = 'deleted_quota'
            query = query.filter( trans.app.model.Quota.table.c.deleted == True )
        else:
            route = 'quota'
            query = query.filter( trans.app.model.Quota.table.c.deleted == False )
        for quota in query:
            item = quota.get_api_value( value_mapper={ 'id': trans.security.encode_id } )
            encoded_id = trans.security.encode_id( quota.id )
            item['url'] = url_for( route, id=encoded_id )
            rval.append( item )
        return rval

    @web.expose_api
    @web.require_admin
    def show( self, trans, id, deleted=False, **kwd ):
        """
        GET /api/quotas/{encoded_quota_id}
        GET /api/quotas/deleted/{encoded_quota_id}
        Displays information about a quota.
        """
        try:
            quota = get_quota_for_access( trans, id, deleted=deleted )
        except BadRequestException, e:
            return str( e )
        return quota.get_api_value( view='element', value_mapper={ 'id': trans.security.encode_id } )
    
    @web.expose_api
    @web.require_admin
    def create( self, trans, payload, **kwd ):
        """
        POST /api/quotas
        Creates a new quota.
        """
        try:
            self._validate_in_users_and_groups( trans, payload )
        except Exception, e:
            trans.response.status = 400
            return str( e )

        status, result = trans.webapp.controllers['admin'].create_quota( trans, cntrller='api', **payload )
        if status != 200 or type( result ) != trans.app.model.Quota:
            trans.response.status = status
            return str( result )
        else:
            encoded_id = trans.security.encode_id( result.id )
            return dict( id = encoded_id,
                         name = result.name,
                         url = url_for( 'quotas', id=encoded_id ) )

    @web.expose_api
    @web.require_admin
    def update( self, trans, id, payload, **kwd ):
        """
        PUT /api/quotas/{encoded_quota_id}
        Modifies a quota.
        """
        try:
            self._validate_in_users_and_groups( trans, payload )
            quota = get_quota_for_access( trans, id, deleted=False ) # deleted quotas are not technically members of this collection
        except Exception, e:
            trans.response.status = 400
            return str( e )
        # TODO: Doing it this way makes the update non-atomic if a method fails after an earlier one has succeeded.
        payload['id'] = id
        methods = []
        if payload.get( 'name', None ) or payload.get( 'description', None ):
            methods.append( trans.webapp.controllers['admin'].rename_quota )
        if payload.get( 'amount', None ):
            methods.append( trans.webapp.controllers['admin'].edit_quota )
        if payload.get( 'default', None ) == 'no':
            methods.append( trans.webapp.controllers['admin'].unset_quota_default )
        elif payload.get( 'default', None ):
            methods.append( trans.webapp.controllers['admin'].set_quota_default )
        if payload.get( 'in_users', None ) or payload.get( 'in_groups', None ):
            methods.append( trans.webapp.controllers['admin'].manage_users_and_groups_for_quota )

        messages = []
        for method in methods:
            status, result = method( trans, cntrller='api', **payload )
            if status != 200:
                trans.response.status = status
                return str( result )
            messages.append( result )
        return '; '.join( messages )

    @web.expose_api
    @web.require_admin
    def delete( self, trans, id, **kwd ):
        """
        DELETE /api/quotas/{encoded_quota_id}
        Deletes a quota
        """
        try:
            get_quota_for_access( trans, id, deleted=False ) # deleted quotas are not technically members of this collection
        except BadRequestException, e:
            return str( e )
        # a request body is optional here
        payload = kwd.get( 'payload', {} )
        payload['id'] = id

        status, result = trans.webapp.controllers['admin'].mark_quota_deleted( trans, cntrller='api', **payload )
        if status != 200:
            trans.response.status = status
            return str( result )
        rval = result

        if util.string_as_bool( payload.get( 'purge', False ) ):
            status, result = trans.webapp.controllers['admin'].purge_quota( trans, cntrller='api', **payload )
            if status != 200:
                trans.response.status = status
                return str( result )
            rval += '; %s' % result
        return rval

    @web.expose_api
    @web.require_admin
    def undelete( self, trans, id, **kwd ):
        """
        POST /api/quotas/deleted/{encoded_quota_id}/undelete
        Undeletes a quota
        """
        status, result = trans.webapp.controllers['admin'].undelete_quota( trans, cntrller='api', id=id )
        if status != 200:
            trans.response.status = status
            return str( result )
        return result

    def _validate_in_users_and_groups( self, trans, payload ):
        """
        For convenience, in_users and in_groups can be encoded IDs or emails/group names
        """
        def get_id( item, model_class, column ):
            try:
                return trans.security.decode_id( item )
            except:
                pass # maybe an email/group name
            # this will raise if the item is invalid
            return trans.sa_session.query( model_class ).filter( column == item ).first().id
        new_in_users = []
        new_in_groups = []
        invalid = []
        for item in util.listify( payload.get( 'in_users', [] ) ):
            try:
                new_in_users.append( get_id( item, trans.app.model.User, trans.app.model.User.table.c.email ) )
            except:
                invalid.append( item )
        for item in util.listify( payload.get( 'in_groups', [] ) ):
            try:
                new_in_groups.append( get_id( item, trans.app.model.Group, trans.app.model.Group.table.c.name ) )
            except:
                invalid.append( item )
        if invalid:
            msg = "The following value(s) for associated users and/or groups could not be parsed: %s." % ', '.join( invalid )
            msg += "  Valid values are email addresses of users, names of groups, or IDs of both."
            raise Exception( msg )
        payload['in_users'] = map( str, new_in_users )
        payload['in_groups'] = map( str, new_in_groups )
