import logging
import galaxy.util.shed_util_common as suc
from galaxy import web
from galaxy.web.base.controller import BaseAPIController

import pkg_resources
pkg_resources.require( "Routes" )
import routes

log = logging.getLogger( __name__ )

class RepositoryContentsController( BaseAPIController ):
    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/repositories/{encoded_repository_id}/contents
        Displays a collection (dictionary) of repository contents.

        :param repository_id: an encoded id string of the `Repository` to inspect
        """
        rval = []
        repository_id = kwd.get( 'repository_id', None )
        try:
            repository = suc.get_repository_in_tool_shed( trans, repository_id )
            value_mapper={ 'id' : repository_id,
                           'user_id' : trans.security.encode_id( repository.user_id ) }
            repository_dict = repository.as_dict( value_mapper )
            repository_dict[ 'url' ] = web.url_for( 'repository_contents', repository_id=repository_id )
            rval.append( repository_dict )
        except Exception, e:
            message = "Error in the Tool Shed  repository_contents API in index: %s" % str( e )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return message
        return rval
