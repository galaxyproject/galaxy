"""
API operations on Galaxy's installed tools.
"""
import logging
from galaxy import exceptions
from galaxy.managers import repos
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import require_admin
from galaxy.web.base.controller import BaseAPIController

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
        * GET /api/admin/repos:
            Return a list of all installed repositories on this instance.

        :returns:   list of repos
        :rtype:     list
        """
        repos = self.repo_manager.list( trans, view='tools' )
        repo_list = []
        for repo in repos:
            repo_dict = self.repo_serializer.serialize_to_view( repo, view='summary')
            if repo.includes_tools:
                repo_dict['type'] = 'tools'
            if repo.provides_only_tool_dependencies:
                repo_dict['type'] = 'packages'
            repo_dict['update'] = 'up to date'
            if repo.revision_update_available:
                repo_dict['update'] = 'minor update'
            if repo.upgrade_available:
                repo_dict['update'] = 'new version'
            repo_list.append( repo_dict )
        unique_dicts = self._list_unique_repos( repo_list )
        unique_dicts_w_sections = self._add_all_sections_for_repo( trans, unique_dicts )
        return self._strip_dicts( unique_dicts_w_sections.values() )

    @expose_api
    @require_admin
    def show( self, trans, id, **kwd ):
        """
        * GET /api/admin/repos/{encoded_id}:
            Return a detail of the installed repository identified
            by the given id.

        :param  id:      the encoded id of the repo
        :type   id:      an encoded id string

        :returns:   detailed repo information
        :rtype:     dictionary
        """
        # TODO respect `view` that is requested
        repo = self.repo_manager.get( trans, self.__decode_id( trans, id, 'repository' ) )
        repo_dict = self.repo_serializer.serialize_to_view( repo, view='summary')
        return repo_dict

    def _strip_dicts( self, repo_dicts ):
        """
        Minimize the size of returning dicts.
        """
        for repo in repo_dicts:
            if 'sections' in repo.keys():
                repo['sections'] = list(repo['sections'])
            repo.pop('tool_shed', '')
            if 'collapsed_repos' in repo.keys():
                for r in repo['collapsed_repos']:
                    # drop this unwanted key
                    r.pop('tool_shed', '')
        return repo_dicts

    def _list_unique_repos( self, all_repos ):
        """
        Given the list of serialized ToolShedRepository objects
        this method will identify those that differ only in revision
        (i.e. have same name, owner and tool_shed) and collapses
        the additional revisions into new attribute 'collapsed_repos'.
        """
        unique_repos = {}
        repos_to_collapse = {}
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
                repos_to_collapse[ repo_a['id'] ] = repo_a
                # store the trio identifying the already collapsed repo
                collapsed_trios.add( repo_a['name'] + repo_a['owner'] + repo_a['tool_shed'] )
            else:
                unique_repos[ repo_a['id'] ] = repo_a
        unique_repos.update( repos_to_collapse )
        return unique_repos

    def _add_all_sections_for_repo( self, trans, unique_dicts ):
        """"
        Iterate over toolbox and enrich the repository dictionaries
        with data of what sections the repo's tools are in.
        """
        for tool in trans.app.toolbox.tools():
            if tool[1].tool_shed:
                tool_dict = tool[1].to_dict( trans )
                repo_id = tool_dict['tool_shed_repository']['id']
                if repo_id in unique_dicts.keys():
                    unique_dicts[repo_id]['sections'] = set()
                    if tool_dict['panel_section_id'] is not None:
                        unique_dicts[repo_id]['sections'].add( tool_dict['panel_section_id'] )
                else:
                    # this will happen when repository has more installable revision installed
                    # and we have no reason to care unless the different versions are in
                    # different sections - ignored as extreme cornercase
                    pass
        return unique_dicts

    def __decode_id( self, trans, encoded_id, object_name=None ):
        """
        Try to decode the id.

        :param  object_name:      Name of the object the id belongs to. (optional)
        :type   object_name:      str

        :raises: MalformedId
        """
        try:
            return trans.security.decode_id( encoded_id )
        except TypeError:
            raise exceptions.MalformedId( 'Malformed %s id specified, unable to decode.' % object_name if object_name is not None else '' )
        except ValueError:
            raise exceptions.MalformedId( 'Wrong %s id specified, unable to decode.' % object_name if object_name is not None else '' )
