import tool_shed.util.shed_util_common as suc
from galaxy import web, util
from galaxy.web.base.controller import BaseAPIController
from galaxy.web.framework.helpers import is_true

import pkg_resources
pkg_resources.require( "Routes" )
import routes
import logging

log = logging.getLogger( __name__ )

class RepositoriesController( BaseAPIController ):
    """RESTful controller for interactions with repositories in the Tool Shed."""
    @web.expose_api
    def index( self, trans, deleted=False, **kwd ):
        """
        GET /api/repository_revisions
        Displays a collection (list) of repositories.
        """
        rval = []
        deleted = util.string_as_bool( deleted )
        try:
            query = trans.sa_session.query( trans.app.model.Repository ) \
                                    .filter( trans.app.model.Repository.table.c.deleted == deleted ) \
                                    .order_by( trans.app.model.Repository.table.c.name ) \
                                    .all()
            for repository in query:
                value_mapper={ 'id' : trans.security.encode_id( repository.id ),
                               'user_id' : trans.security.encode_id( repository.user_id ) }
                item = repository.get_api_value( view='collection', value_mapper=value_mapper )
                item[ 'url' ] = web.url_for( 'repository_contents', repository_id=trans.security.encode_id( repository.id ) )
                rval.append( item )
        except Exception, e:
            message = "Error in the Tool Shed repositories API in index: %s" % str( e )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return message
        return rval
    @web.expose_api
    def show( self, trans, id, **kwd ):
        """
        GET /api/repositories/{encoded_repository_id}
        Displays information about a repository in the Tool Shed.
        """
        try:
            repository = suc.get_repository_in_tool_shed( trans, id )
            value_mapper={ 'id' : trans.security.encode_id( repository.id ),
                           'user_id' : trans.security.encode_id( repository.user_id ) }
            repository_data = repository.get_api_value( view='element', value_mapper=value_mapper )
            repository_data[ 'contents_url' ] = web.url_for( 'repository_contents', repository_id=id )
        except Exception, e:
            message = "Error in the Tool Shed repositories API in show: %s" % str( e )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return message
        return repository_data
