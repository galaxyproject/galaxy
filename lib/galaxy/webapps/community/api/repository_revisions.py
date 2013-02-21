import galaxy.util.shed_util_common as suc
from galaxy import web, util
from galaxy.web.base.controller import BaseAPIController
from galaxy.web.framework.helpers import is_true

import pkg_resources
pkg_resources.require( "Routes" )
import routes
import logging

log = logging.getLogger( __name__ )

class RepositoryRevisionsController( BaseAPIController ):
    """RESTful controller for interactions with tool shed repository revisions."""
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
                item = repository_metadata.get_api_value( value_mapper={ 'id' : trans.security.encode_id( repository_metadata.id ) } )
                item[ 'url' ] = web.url_for( 'repository_revision', id=trans.security.encode_id( repository_metadata.id ) )
                rval.append( item )
        except Exception, e:
            rval = "Error in repository_revisions API at index: " + str( e )
            log.error( rval + ": %s" % str( e ) )
            trans.response.status = 500
        return rval
