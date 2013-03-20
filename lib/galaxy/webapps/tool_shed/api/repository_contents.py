import logging
import tool_shed.util.shed_util_common as suc
from galaxy import web
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger( __name__ )


class RepositoryContentsController( BaseAPIController ):

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/repositories/{encoded_repository_id}
        Displays a collection (dictionary) of repository contents.

        :param repository_id: the encoded id of the `Repository` object
        """
        try:
            repository_id = kwd[ 'repository_id' ]
            repository = suc.get_repository_in_tool_shed( trans, repository_id )
            value_mapper={ 'id' : trans.security.encode_id( repository.id ),
                           'user_id' : trans.security.encode_id( repository.user_id ) }
            repository_dict = repository.as_dict( value_mapper )
            repository_dict[ 'url' ] = web.url_for( controller='repository_contents',
                                                    action='index',
                                                    repository_id=repository_id )
            return repository_dict
        except Exception, e:
            message = "Error in the Tool Shed  repository_contents API in index: %s" % str( e )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return message
