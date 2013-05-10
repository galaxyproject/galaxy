import logging
from galaxy.web.framework.helpers import time_ago
from galaxy import web
from galaxy import util
from galaxy.web.base.controller import BaseAPIController
import tool_shed.util.shed_util_common as suc
from tool_shed.galaxy_install import repository_util

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

    @web.expose_api_anonymous
    def get_ordered_installable_revisions( self, trans, name, owner, **kwd ):
        """
        GET /api/repository/get_ordered_installable_revisions
        
        :param name: the name of the Repository
        :param owner: the owner of the Repository
        
        Returns the ordered list of changeset revision hash strings that are associated with installable revisions.  As in the changelog, the
        list is ordered oldest to newest.
        """
        # Example URL: http://localhost:9009/api/repositories/get_installable_revisions?name=add_column&owner=test
        try:
            # Get the repository information.
            repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
            encoded_repository_id = trans.security.encode_id( repository.id )
            repo_dir = repository.repo_path( trans.app )
            repo = hg.repository( suc.get_configured_ui(), repo_dir )
            ordered_installable_revisions = suc.get_ordered_metadata_changeset_revisions( repository, repo, downloadable=True )
            return ordered_installable_revisions
        except Exception, e:
            message = "Error in the Tool Shed repositories API in get_ordered_installable_revisions: %s" % str( e )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return message

    @web.expose_api_anonymous
    def get_repository_revision_install_info( self, trans, name, owner, changeset_revision, **kwd ):
        """
        GET /api/repository/get_repository_revision_install_info
        
        :param name: the name of the Repository
        :param owner: the owner of the Repository
        :param changset_revision: the changset_revision of the RepositoryMetadata object associated with the Repository
        
        Returns a list of the following dictionaries::
        - a dictionary defining the Repository.  For example:
        {
            "deleted": false, 
            "deprecated": false, 
            "description": "add_column hello", 
            "id": "f9cad7b01a472135", 
            "long_description": "add_column hello", 
            "name": "add_column", 
            "owner": "test", 
            "private": false, 
            "times_downloaded": 6, 
            "url": "/api/repositories/f9cad7b01a472135", 
            "user_id": "f9cad7b01a472135"
        }
        - a dictionary defining the Repository revision (RepositoryMetadata).  For example:
        {
            "changeset_revision": "3a08cc21466f", 
            "downloadable": true, 
            "has_repository_dependencies": false, 
            "id": "f9cad7b01a472135", 
            "includes_datatypes": false, 
            "includes_tool_dependencies": false, 
            "includes_tools": true,
            "includes_tools_for_display_in_tool_panel": true,
            "includes_workflows": false, 
            "malicious": false, 
            "repository_id": "f9cad7b01a472135", 
            "url": "/api/repository_revisions/f9cad7b01a472135"
        }
        - a dictionary including the additional information required to install the repository.  For example:
        {
            "add_column": [
                "add_column hello", 
                "http://test@localhost:9009/repos/test/add_column", 
                "3a08cc21466f", 
                "1", 
                "test", 
                {}, 
                {}
            ]
        }
        """
        # Example URL: http://localhost:9009/api/repositories/get_repository_revision_install_info?name=add_column&owner=test&changeset_revision=3a08cc21466f
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
                changeset_revision = new_changeset_revision
            if repository_metadata:
                encoded_repository_metadata_id = trans.security.encode_id( repository_metadata.id )
                repository_metadata_dict = repository_metadata.get_api_value( view='collection',
                                                                              value_mapper=default_repository_metadata_value_mapper( trans, repository_metadata ) )
                repository_metadata_dict[ 'url' ] = web.url_for( controller='repository_revisions',
                                                                 action='show',
                                                                 id=encoded_repository_metadata_id )
                # Get the repo_info_dict for installing the repository.
                repo_info_dict, includes_tools, includes_tool_dependencies, includes_tools_for_display_in_tool_panel, has_repository_dependencies = \
                    repository_util.get_repo_info_dict( trans, encoded_repository_id, changeset_revision )
                return repository_dict, repository_metadata_dict, repo_info_dict
            else:
                message = "Unable to locate repository_metadata record for repository id %d and changeset_revision %s" % ( repository.id, changeset_revision )
                log.error( message, exc_info=True )
                trans.response.status = 500
                return repository_dict, {}, {}
        except Exception, e:
            message = "Error in the Tool Shed repositories API in get_repository_revision_install_info: %s" % str( e )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return message

    @web.expose_api_anonymous
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

    @web.expose_api_anonymous
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
