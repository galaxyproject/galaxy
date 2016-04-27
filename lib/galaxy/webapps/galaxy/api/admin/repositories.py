"""
API operations on Galaxy's installed tools.
"""
from galaxy import util
from galaxy import exceptions
from galaxy.managers import repos
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import require_admin
from galaxy.web.base.controller import BaseAPIController

import logging
log = logging.getLogger( __name__ )


class RepositoriesController( BaseAPIController ):

    def __init__( self, app ):
        self.repo_manager = repos.RepoManager(app)
        self.repo_serializer = repos.RepositorySerializer( app )
        super( RepositoriesController, self ).__init__( app )

    @expose_api
    @require_admin
    def index( self, trans, **kwd ):
        """
        * GET /api/admin/repositories:
            Returns a list of all installed repositories on this instance.

        :returns:   list of repos
        :rtype:     list

        """
        repos = self.repo_manager.list( trans, view='with_tools' )
        return_dict = []
        for repo in repos:
            repo_dict = self.repo_serializer.serialize_to_view( repo, view='summary')
            if repo.includes_tools:
                repo_dict['type'] = 'with_tools'
            if repo.provides_only_tool_dependencies:
                repo_dict['type'] = 'tool_dependencies'
            return_dict.append( repo_dict )
        return return_dict
