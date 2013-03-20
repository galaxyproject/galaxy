import logging
import tool_shed.util.shed_util_common as suc
from galaxy import web, util
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger( __name__ )


class RepositoriesController( BaseAPIController ):
    """RESTful controller for interactions with repositories in the Tool Shed."""

    @web.expose_api
    def index( self, trans, deleted=False, **kwd ):
        """
        GET /api/repositories
        Displays a collection (list) of repositories.
        """
        repository_dicts = []
        deleted = util.string_as_bool( deleted )
        try:
            query = trans.sa_session.query( trans.app.model.Repository ) \
                                    .filter( trans.app.model.Repository.table.c.deleted == deleted ) \
                                    .order_by( trans.app.model.Repository.table.c.name ) \
                                    .all()
            for repository in query:
                value_mapper={ 'id' : trans.security.encode_id( repository.id ),
                               'user_id' : trans.security.encode_id( repository.user_id ) }
                repository_dict = repository.get_api_value( view='collection', value_mapper=value_mapper )
                repository_dict[ 'url' ] = web.url_for( controller='repository_contents',
                                                        action='index',
                                                        repository_id=trans.security.encode_id( repository.id ) )
                repository_dicts.append( repository_dict )
            return repository_dicts
        except Exception, e:
            message = "Error in the Tool Shed repositories API in index: %s" % str( e )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return message

    @web.expose_api
    def show( self, trans, id, **kwd ):
        """
        GET /api/repositories/{encoded_repository_id}
        Displays information about a repository in the Tool Shed.
        
        :param id: the encoded id of the `Repository` object
        """
        try:
            repository = suc.get_repository_in_tool_shed( trans, id )
            value_mapper={ 'id' : trans.security.encode_id( repository.id ),
                           'user_id' : trans.security.encode_id( repository.user_id ) }
            repository_dict = repository.get_api_value( view='element', value_mapper=value_mapper )
            repository_dict[ 'url' ] = web.url_for( controller='repository_contents',
                                                    action='index',
                                                    repository_id=trans.security.encode_id( repository.id ) )
            return repository_dict
        except Exception, e:
            message = "Error in the Tool Shed repositories API in show: %s" % str( e )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return message
