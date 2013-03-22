import logging
from galaxy.web.framework.helpers import time_ago
import tool_shed.util.shed_util_common as suc
from galaxy import web
from galaxy import util
from galaxy.web.base.controller import BaseAPIController

from galaxy import eggs
import pkg_resources

pkg_resources.require( 'mercurial' )
from mercurial import hg, ui, commands

log = logging.getLogger( __name__ )

def default_repository_value_mapper( trans, repository ):
    value_mapper={ 'id' : trans.security.encode_id( repository.id ),
                   'user_id' : trans.security.encode_id( repository.user_id ) }
    return value_mapper

def default_repository_metadata_value_mapper( trans, repository_metadata ):
    value_mapper = { 'id' : trans.security.encode_id( repository_metadata.id ),
                     'repository_id' : trans.security.encode_id( repository_metadata.repository_id ) }
    if repository_metadata.time_last_tested:
        value_mapper[ 'time_last_tested' ] = time_ago( repository_metadata.time_last_tested )
    return value_mapper


class RepositoriesController( BaseAPIController ):
    """RESTful controller for interactions with repositories in the Tool Shed."""

    @web.expose_api
    def index( self, trans, deleted=False, **kwd ):
        """
        GET /api/repositories
        Displays a collection (list) of repositories.
        """
        # Example URL: http://localhost:9009/api/repositories
        repository_dicts = []
        deleted = util.string_as_bool( deleted )
        try:
            query = trans.sa_session.query( trans.app.model.Repository ) \
                                    .filter( trans.app.model.Repository.table.c.deleted == deleted ) \
                                    .order_by( trans.app.model.Repository.table.c.name ) \
                                    .all()
            for repository in query:
                repository_dict = repository.get_api_value( view='collection', value_mapper=default_repository_value_mapper( trans, repository ) )
                repository_dict[ 'url' ] = web.url_for( controller='repositories',
                                                        action='show',
                                                        id=trans.security.encode_id( repository.id ) )
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
        Returns information about a repository in the Tool Shed.
        
        :param id: the encoded id of the Repository object
        """
        # Example URL: http://localhost:9009/api/repositories/f9cad7b01a472135
        try:
            repository = suc.get_repository_in_tool_shed( trans, id )
            repository_dict = repository.get_api_value( view='element', value_mapper=default_repository_value_mapper( trans, repository ) )
            repository_dict[ 'url' ] = web.url_for( controller='repositories',
                                                    action='show',
                                                    id=trans.security.encode_id( repository.id ) )
            return repository_dict
        except Exception, e:
            message = "Error in the Tool Shed repositories API in show: %s" % str( e )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return message

    @web.expose_api
    def get_repository_and_revision( self, trans, name, owner, changeset_revision, **kwd ):
        """
        GET /api/repository/get_repository_and_revision
        Returns information about a repository revision in the Tool Shed.
        
        :param name: the name of the Repository object
        :param owner: the owner of the Repository object
        :param changset_revision: the changset_revision of the RepositoryMetadata object associated with the Repository object
        """
        # Example URL: http://localhost:9009/api/repositories/get_repository_and_revision?name=add_column&owner=test&changeset_revision=3a08cc21466f
        try:
            # Get the repository information.
            repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
            encoded_repository_id = trans.security.encode_id( repository.id )
            repository_dict = repository.get_api_value( view='element', value_mapper=default_repository_value_mapper( trans, repository ) )
            repository_dict[ 'url' ] = web.url_for( controller='repositories',
                                                    action='show',
                                                    id=encoded_repository_id )
            # Get the repository_metadata information.
            repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, encoded_repository_id, changeset_revision )
            if not repository_metadata:
                # The changeset_revision column in the repository_metadata table has been updated with a new value value, so find the
                # changeset_revision to which we need to update.
                repo_dir = repository.repo_path( trans.app )
                repo = hg.repository( suc.get_configured_ui(), repo_dir )
                new_changeset_revision = suc.get_next_downloadable_changeset_revision( repository, repo, changeset_revision )
                repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, encoded_repository_id, new_changeset_revision )
            if repository_metadata:
                encoded_repository_metadata_id = trans.security.encode_id( repository_metadata.id )
                repository_metadata_dict = repository_metadata.get_api_value( view='collection',
                                                                              value_mapper=default_repository_metadata_value_mapper( trans, repository_metadata ) )
                repository_metadata_dict[ 'url' ] = web.url_for( controller='repository_revisions',
                                                                 action='show',
                                                                 id=encoded_repository_metadata_id )
                return repository_dict, repository_metadata_dict
            else:
                message = "Unable to locate repository_metadata record for repository id %d and changeset_revision %s" % ( repository.id, changeset_revision )
                log.error( message, exc_info=True )
                trans.response.status = 500
                return repository_dict, {}
        except Exception, e:
            message = "Error in the Tool Shed repositories API in get_repository_and_revision: %s" % str( e )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return message
