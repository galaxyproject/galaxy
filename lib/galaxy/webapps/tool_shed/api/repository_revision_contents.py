import logging
from galaxy import web
from galaxy.web.framework.helpers import time_ago
from tool_shed.util import metadata_util
from galaxy.web.base.controller import BaseAPIController

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
        GET /api/repository_revisions/{encoded_repository_metadata_id}
        Displays a collection (dictionary) of repository_metadata contents.

        :param repository_metadata_id: the encoded id of the `RepositoryMetadata` object
        """
        try:
            repository_metadata_id = kwd.get( 'repository_metadata_id', None )
            repository_metadata = metadata_util.get_repository_metadata_by_id( trans, repository_metadata_id )
            repository_dict = repository_metadata.as_dict( value_mapper=default_value_mapper( trans, repository_metadata ) )
            repository_dict[ 'url' ] = web.url_for( controller='repository_revision_contents',
                                                    action='index',
                                                    repository_metadata_id=repository_metadata_id )
            return repository_dict
        except Exception, e:
            message = "Error in the Tool Shed repository_revision_contents API in index: %s" % str( e )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return message
