import logging
from galaxy.web.framework.helpers import time_ago
import tool_shed.util.shed_util_common as suc
from galaxy import web
from galaxy.web.base.controller import BaseAPIController

import pkg_resources
pkg_resources.require( "Routes" )
import routes

log = logging.getLogger( __name__ )

def default_value_mapper( trans, repository_metadata ):
    value_mapper = { 'id' : trans.security.encode_id( repository_metadata.id ),
                     'repository_id' : trans.security.encode_id( repository_metadata.repository_id ) }
    if repository_metadata.time_last_tested:
        value_mapper[ 'time_last_tested' ] = time_ago( repository_metadata.time_last_tested )
    return value_mapper

class RepositoryRevisionContentsController( BaseAPIController ):
    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/repository_revisions/{encoded_repository_metadata_id}/contents
        Displays a collection (dictionary) of repository_metadata contents.

        :param repository_metadata_id: an encoded id string of the `RepositoryMetadata` to inspect
        """
        rval = []
        repository_metadata_id = kwd.get( 'repository_metadata_id', None )
        try:
            repository_metadata = suc.get_repository_metadata_by_id( trans, repository_metadata_id )
            repository_dict = repository_metadata.as_dict( value_mapper=default_value_mapper( trans, repository_metadata ) )
            repository_dict[ 'url' ] = web.url_for( 'repository_revision_contents', repository_metadata_id=repository_metadata_id )
            rval.append( repository_dict )
        except Exception, e:
            message = "Error in the Tool Shed  repository_revision_contents API in index: %s" % str( e )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return message
        return rval
