from galaxy import web, util, logging
from galaxy.web.base.controller import BaseController, BaseAPIController
from galaxy.web.framework.helpers import is_true

import pkg_resources
pkg_resources.require( "Routes" )
import routes

log = logging.getLogger( __name__ )

class RepositoryRevisionsController( BaseAPIController ):
    """RESTful controller for interactions with tool shed repositories."""
    @web.expose_api
    def index( self, trans, downloadable=True, **kwd ):
        """
        GET /api/repository_revisions
        Displays a collection (list) of repository revisions.
        """
        rval = []
        downloadable = util.string_as_bool( downloadable )
        try:
            query = trans.sa_session.query( trans.app.model.RepositoryMetadata ) \
                                    .filter( trans.app.model.RepositoryMetadata.table.c.downloadable == downloadable ) \
                                    .order_by( trans.app.model.RepositoryMetadata.table.c.repository_id ) \
                                    .all()
            for repository_metadata in query:
                item = repository_metadata.get_api_value( value_mapper={ 'id' : trans.security.encode_id } )
                item[ 'url' ] = web.url_for( 'repository_revision', id=trans.security.encode_id( repository_metadata.id ) )
                rval.append( item )
        except Exception, e:
            rval = "Error in repository_revisions API"
            log.error( rval + ": %s" % str( e ) )
            trans.response.status = 500
        return rval
