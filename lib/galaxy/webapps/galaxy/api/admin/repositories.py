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
            Return a list of all installed repositories on this instance.

        :returns:   list of repos
        :rtype:     list

        """
        repos = self.repo_manager.list( trans, view='tools' )
        return_dict = []
        for repo in repos:
            repo_dict = self.repo_serializer.serialize_to_view( repo, view='summary')
            if repo.includes_tools:
                repo_dict['type'] = 'tools'
            if repo.provides_only_tool_dependencies:
                repo_dict['type'] = 'packages'
            return_dict.append( repo_dict )
        unique_dict = self._list_unique_repos( return_dict )
        # TODO attach toolpanel section
        # log.debug(trans.app.toolbox.__dict__)
        # log.debug(str(trans.app.toolbox.tools))
        # log.debug([str(tool) for tool in trans.app.toolbox.to_dict(trans)])

        log.debug([str(tool[1].to_dict(trans)) for tool in trans.app.toolbox.tools()])
        return unique_dict

    def _list_unique_repos( self, all_repos ):
        """
        Given the list of serialized ToolShedRepository objects
        this method will identify those that differ only in revision
        (i.e. have same name, owner and tool_shed) and collapses
        the additional revisions into new attribute 'collapsed_repos'.
        """
        unique_repos = []
        repos_to_collapse = []
        collapsed_trios = set()
        for repo_a in all_repos:
            if ( repo_a['name'] + repo_a['owner'] + repo_a['tool_shed'] ) in collapsed_trios:
                # the repository is already collapsed, continue
                continue
            collapsed_repos = []
            for repo_b in all_repos:
                if repo_a['id'] == repo_b['id']:
                    # we found identity, ignore
                    continue
                if repo_a['name'] == repo_b['name'] and repo_a['owner'] == repo_b['owner'] and repo_a['tool_shed'] == repo_b['tool_shed']:
                    # we found another revision of repo_a, store
                    collapsed_repos.append( repo_b.copy() )
                    continue
            if collapsed_repos:
                # if other revision of repo were found, save them within the first repo
                repo_a['collapsed_repos'] = collapsed_repos
                repos_to_collapse.append( repo_a )
                # store the trio identifying the already collapsed repo
                collapsed_trios.add( repo_a['name'] + repo_a['owner'] + repo_a['tool_shed'] )
            else:
                unique_repos.append( repo_a )
        repos_to_collapse.extend(unique_repos)
        return repos_to_collapse
