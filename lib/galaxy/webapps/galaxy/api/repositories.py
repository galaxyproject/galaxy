import json
import logging
import re

from six.moves.urllib.parse import (
    quote as urlquote,
    unquote as urlunquote
)
from sqlalchemy import and_
from galaxy import (
    util,
    web
)
from galaxy.web import expose_api
from galaxy.web.base.controller import BaseAPIController
from tool_shed.util import (
    common_util,
    encoding_util,
    repository_util,
    tool_util
)
import tool_shed.util.shed_util_common as suc
from tool_shed.galaxy_install.install_manager import InstallRepositoryManager

log = logging.getLogger(__name__)


class RepositoriesController(BaseAPIController):
    """RESTful controller for managing repositories."""

    @expose_api
    def index(self, trans, **kwd):
        """
        GET /api/repositories
        Display a list of dictionaries containing information about installed tool shed repositories.
        """
        clause_list = []
        if 'name' in kwd:
            clause_list.append(self.app.install_model.ToolShedRepository.table.c.name == kwd.get('name'))
        if 'owner' in kwd:
            clause_list.append(self.app.install_model.ToolShedRepository.table.c.owner == kwd.get('owner'))
        if 'changeset' in kwd:
            clause_list.append(self.app.install_model.ToolShedRepository.table.c.changeset_revision == kwd.get('changeset'))
        tool_shed_repository_dicts = []
        query = trans.install_model.context.query(self.app.install_model.ToolShedRepository) \
                                           .order_by(self.app.install_model.ToolShedRepository.table.c.name)
        if len(clause_list) > 0:
            query = query.filter(and_(*clause_list))
        for tool_shed_repository in query.all():
            value_mapper = dict(id=trans.security.encode_id(tool_shed_repository.id),
                                error_message=tool_shed_repository.error_message or '')
            tool_shed_repository_dict = tool_shed_repository.to_dict(value_mapper=value_mapper)
            tool_shed_repository_dicts.append(tool_shed_repository_dict)
        return tool_shed_repository_dicts

    @expose_api
    @web.require_admin
    def show(self, trans, id, **kwd):
        """
        GET /api/repositories/{id}
        Return the dictionary representation of repositories.

        :param id: the repository's encoded id
        """
        tool_shed_repository = self.app.install_model.context.query(self.app.install_model.ToolShedRepository) \
                                        .filter(self.app.install_model.ToolShedRepository.table.c.id == self.app.security.decode_id(id)) \
                                        .first()
        if tool_shed_repository is None:
            log.debug("Could not find repository id %s." % (str(id)))
            return {}
        value_mapper = dict(id=trans.security.encode_id(tool_shed_repository.id),
                            error_message=tool_shed_repository.error_message or '')
        tool_shed_repository_dict = tool_shed_repository.as_dict(value_mapper)
        return tool_shed_repository_dict

    @expose_api
    @web.require_admin
    def install(self, trans, payload={}, **kwd):
        """
        POST /api/repositories/install
        Initiate the installation of a repository.

        :param install_resolver_dependencies: True to install resolvable dependencies.
        :param install_tool_dependencies: True to install tool dependencies.
        :param install_repository_dependencies: True to install repository dependencies.
        :param tool_panel_section_id: The unique identifier for an existing tool panel section
        :param new_tool_panel_section_label: Create a new tool panel section with this label
        :param shed_tool_conf: The shed tool config file to use for this installation
        :param tool_shed_url: The URL for the toolshed whence this repository is being installed
        :param changeset: The changeset to update to after cloning the repository
        """
        irm = InstallRepositoryManager(self.app)
        tool_shed_url = payload.get('tool_shed_url', None)
        repositories = payload.get('repositories', [])
        repo_info_dict = self.__get_repo_info_dict(trans, repositories, tool_shed_url)
        includes_tools = False
        includes_tools_for_display_in_tool_panel = False
        has_repository_dependencies = False
        includes_tool_dependencies = False
        install_resolver_dependencies = util.asbool(payload.get('install_resolver_dependencies', False))
        for encoded_repo_info_dict in repo_info_dict.get('repo_info_dicts', []):
            decoded_repo_info_dict = encoding_util.tool_shed_decode(encoded_repo_info_dict)
            if not includes_tools:
                includes_tools = util.string_as_bool(decoded_repo_info_dict.get('includes_tools', False))
            if not includes_tools_for_display_in_tool_panel:
                includes_tools_for_display_in_tool_panel = \
                    util.string_as_bool(decoded_repo_info_dict.get('includes_tools_for_display_in_tool_panel', False))
            if not has_repository_dependencies:
                has_repository_dependencies = util.string_as_bool(repo_info_dict.get('has_repository_dependencies', False))
            if not includes_tool_dependencies:
                includes_tool_dependencies = util.string_as_bool(repo_info_dict.get('includes_tool_dependencies', False))
        encoded_repo_info_dicts = util.listify(repo_info_dict.get('repo_info_dicts', []))
        repo_info_dicts = [encoding_util.tool_shed_decode(encoded_repo_info_dict) for encoded_repo_info_dict in encoded_repo_info_dicts]
        tool_panel_section_id = payload.get('tool_panel_section_id', None)
        new_tool_panel_section_label = payload.get('new_tool_panel_section', None)
        tool_panel_section_mapping = json.loads(payload.get('tool_panel_section', '{}'))
        install_tool_dependencies = util.asbool(payload.get('install_tool_dependencies', False))
        install_repository_dependencies = util.asbool(payload.get('install_repository_dependencies', False))
        shed_tool_conf = payload.get('shed_tool_conf', None)
        tool_path = suc.get_tool_path_by_shed_tool_conf_filename(self.app, shed_tool_conf)
        installation_dict = dict(install_repository_dependencies=install_repository_dependencies,
                                 new_tool_panel_section_label=new_tool_panel_section_label,
                                 no_changes_checked=False,
                                 repo_info_dicts=repo_info_dicts,
                                 tool_panel_section_id=tool_panel_section_id,
                                 tool_path=tool_path,
                                 tool_shed_url=tool_shed_url)
        new_repositories, tool_panel_keys, repo_info_dicts, filtered_repos = irm.handle_tool_shed_repositories(installation_dict)
        if new_repositories:
            installation_dict = dict(created_or_updated_tool_shed_repositories=new_repositories,
                                     filtered_repo_info_dicts=filtered_repos,
                                     has_repository_dependencies=has_repository_dependencies,
                                     includes_tool_dependencies=includes_tool_dependencies,
                                     includes_tools=includes_tools,
                                     includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
                                     install_repository_dependencies=install_repository_dependencies,
                                     install_tool_dependencies=install_tool_dependencies,
                                     message='',
                                     new_tool_panel_section_label=new_tool_panel_section_label,
                                     tool_panel_section_mapping=tool_panel_section_mapping,
                                     install_resolver_dependencies=install_resolver_dependencies,
                                     shed_tool_conf=shed_tool_conf,
                                     status='ok',
                                     tool_panel_section_id=tool_panel_section_id,
                                     tool_panel_section_keys=tool_panel_keys,
                                     tool_path=tool_path,
                                     tool_shed_url=tool_shed_url)
            encoded_kwd, query, tool_shed_repositories, encoded_repository_ids = \
                irm.initiate_repository_installation(installation_dict)
            return json.dumps(dict(operation='install',
                                   api=True,
                                   install_resolver_dependencies=install_resolver_dependencies,
                                   install_tool_dependencies=install_tool_dependencies,
                                   encoded_kwd=encoded_kwd,
                                   reinstalling=False,
                                   tool_shed_repository_ids=json.dumps([repo[0] for repo in repositories]),
                                   repositories=[trans.security.encode_id(repo.id) for repo in new_repositories]))

    def __get_repo_info_dict(self, trans, repositories, tool_shed_url):
        repo_ids = []
        changesets = []
        for repository_id, changeset in repositories:
            repo_ids.append(repository_id)
            changesets.append(changeset)
        params = dict(repository_ids=str(','.join(repo_ids)), changeset_revisions=str(','.join(changesets)))
        pathspec = ['repository', 'get_repository_information']
        raw_text = util.url_get(tool_shed_url, password_mgr=self.app.tool_shed_registry.url_auth(tool_shed_url), pathspec=pathspec, params=params)
        return json.loads(util.unicodify(raw_text))

    @expose_api
    def uninstall(self, trans, id=None, **kwd):
        """
        DELETE /api/repositories/id
        DELETE /api/repositories/

        :param id:  encoded repository id. Either id or name, owner, changeset_revision and tool_shed_url need to be supplied
        :param kwd: 'remove_from_disk'  : Remove repository from disk or deactivate repository.
                                          Defaults to `True` (= remove repository from disk).
                    'name'   : Repository name
                    'owner'  : Repository owner
                    'changeset_revision': Changeset revision to uninstall
                    'tool_shed_url'     : Tool Shed URL
        """
        if id:
            try:
                repository = repository_util.get_tool_shed_repository_by_id(self.app, id)
            except ValueError:
                raise HTTPBadRequest(detail="No repository with id '%s' found" % id)
        else:
            tsr_arguments = ['name', 'owner', 'changeset_revision', 'tool_shed_url']
            try:
                tsr_arguments = {key: kwd[key] for key in tsr_arguments}
            except KeyError as e:
                raise HTTPBadRequest(detail="Missing required parameter '%s'" % e.args[0])
            repository = repository_util.get_installed_repository(app=self.app,
                                                                  tool_shed=tsr_arguments['tool_shed_url'],
                                                                  name=tsr_arguments['name'],
                                                                  owner=tsr_arguments['owner'],
                                                                  changeset_revision=tsr_arguments['changeset_revision'])
            if not repository:
                raise HTTPBadRequest(detail="Repository not found")
        irm = InstalledRepositoryManager(app=self.app)
        errors = irm.uninstall_repository(repository=repository, remove_from_disk=kwd.get('remove_from_disk', True))
        if not errors:
            action = 'removed' if kwd.get('remove_from_disk', True) else 'deactivated'
            return {'message': 'The repository named %s has been %s.' % (repository.name, action)}
        else:
            raise Exception('Attempting to uninstall tool dependencies for repository named %s resulted in errors: %s' % (repository.name, errors))

    @expose_api
    @web.require_admin
    def search(self, trans, tool_shed_url, **params):
        """
        GET /api/tool_shed/search
        Search for a specific repository in the toolshed.
        :param q:          the query string to search for
        :param q:          str
        :param tool_shed_url:   the URL of the toolshed to search
        :param tool_shed_url:   str
        """
        response = json.loads(util.url_get(tool_shed_url, params=dict(params), pathspec=['api', 'repositories']))
        return response

    @expose_api
    @web.require_admin
    def categories(self, trans, tool_shed_url):
        """
        GET /api/tool_shed/categories
        List all available categories
        """
        response = json.loads(util.url_get(tool_shed_url, pathspec=['api', 'categories']))
        return response

    @expose_api
    @web.require_admin
    def details(self, trans, tool_shed_url, repository_id):
        """
        GET /api/tool_shed/details
        Return details for a given repository id
        """
        response = json.loads(util.url_get(tool_shed_url, pathspec=['api', 'repositories', repository_id, 'metadata']))
        return response
