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
    def index( self, trans, repository_id, **kwd ):
        """
        GET /api/repositories/{encoded_repsository_id}/contents
        Displays a collection (list) of repository contents.

        :param repository_id: an encoded id string of the `Repository` to inspect
        """
        rval = []
        try:
            repository = suc.get_repository_in_tool_shed( trans, repository_id )
            repository_dict = repository.as_dict( trans )
            repository_dict[ 'url' ] = web.url_for( 'repository_contents', repository_id=repository_id )
            rval.append( repository_dict )
        except Exception, e:
            message = "Error in repository_contents API: %s" % str( e )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return message
        return rval
