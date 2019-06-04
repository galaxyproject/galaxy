import json
import logging
import re

from six.moves.urllib.parse import (
    quote as urlquote,
    unquote as urlunquote
)
from sqlalchemy import and_, or_
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
from tool_shed.galaxy_install.installed_repository_manager import InstalledRepositoryManager
from tool_shed.galaxy_install.tools.tool_panel_manager import ToolPanelManager

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
        :param id: encoded repository id
        """
        encoded_id = self.app.security.decode_id(id)
        tool_shed_repository = self.app.install_model.context.query(self.app.install_model.ToolShedRepository) \
                                        .filter(self.app.install_model.ToolShedRepository.table.c.id == encoded_id) \
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

        :param repositories: The repository id and changeset tuple array
        :param install_resolver_dependencies: True to install resolvable dependencies.
        :param install_tool_dependencies: True to install tool dependencies.
        :param install_repository_dependencies: True to install repository dependencies.
        :param tool_section: Existing or new tool panel section with this label
        :param tool_configuration: The shed tool config file to use for this installation
        :param tool_shed_url: The URL for the toolshed whence this repository is being installed
        """
        irm = InstallRepositoryManager(self.app)
        install_resolver_dependencies = util.asbool(payload.get('install_resolver_dependencies'))
        install_tool_dependencies = util.asbool(payload.get('install_tool_dependencies'))
        install_repository_dependencies = util.asbool(payload.get('install_repository_dependencies'))
        repositories = payload.get('repositories', [])
        tool_configuration = payload.get('tool_configuration')
        tool_section = payload.get('tool_section')
        tool_panel_section_mapping = payload.get('tool_panel_section', {})
        tool_shed_url = payload.get('tool_shed_url')
        if not tool_shed_url:
            raise Exception('tool_shed_url missing.')
        if not repositories:
            raise Exception('repositories missing.')
        if not tool_configuration:
            raise Exception('tool_configuration missing.')
        # collect tool panel settings
        tool_panel_section_id = None
        new_tool_panel_section_label = None
        sections = self.app.toolbox.get_sections()
        if tool_section:
            tool_section_lower = tool_section.lower().strip()
            for section_id, section_name in sections:
                if tool_section_lower == section_name.lower().strip():
                    tool_panel_section_id = section_id
                    break
            if tool_panel_section_id is None:
                new_tool_panel_section_label = tool_section
        # encode repository dictionaries
        repo_info_dict = self._get_repo_info_dict(trans, repositories, tool_shed_url)
        includes_tools = False
        includes_tools_for_display_in_tool_panel = False
        has_repository_dependencies = False
        includes_tool_dependencies = False
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
        tool_path = suc.get_tool_path_by_shed_tool_conf_filename(self.app, tool_configuration)
        installation_dict = dict(install_repository_dependencies=install_repository_dependencies,
                                 new_tool_panel_section_label=new_tool_panel_section_label,
                                 no_changes_checked=False,
                                 repo_info_dicts=repo_info_dicts,
                                 tool_panel_section_id=tool_panel_section_id,
                                 tool_path=tool_path,
                                 tool_shed_url=tool_shed_url)
        new_repositories, tool_panel_keys, repo_info_dicts, filtered_repos = irm.handle_tool_shed_repositories(installation_dict)
        if new_repositories:
            # Handle tool sections
            tpm = ToolPanelManager(self.app)
            if includes_tools_for_display_in_tool_panel and (new_tool_panel_section_label or tool_panel_section_id):
                tpm.handle_tool_panel_section(self.app.toolbox,
                                              tool_panel_section_id=tool_panel_section_id,
                                              new_tool_panel_section_label=new_tool_panel_section_label)
        else:
            raise Exception('Repositories not found.')
        # Build dictionaries to install the repositories
        encoded_repository_ids = [self.app.security.encode_id(r.id) for r in new_repositories]
        decoded_repository_ids = [r.id for r in new_repositories]
        if encoded_repository_ids:
            # Obtain repositories from database
            tool_shed_repositories = []
            self.install_model = self.app.install_model
            for tsr_id in decoded_repository_ids:
                tsr = self.install_model.context.query(self.install_model.ToolShedRepository).get(tsr_id)
                tool_shed_repositories.append(tsr)
            clause_list = []
            for tsr_id in decoded_repository_ids:
                clause_list.append(self.install_model.ToolShedRepository.table.c.id == tsr_id)
            query = self.install_model.context.query(self.install_model.ToolShedRepository).filter(or_(*clause_list))
            # Install repositories
            decoded_kwd = dict(
                install_resolver_dependencies=install_resolver_dependencies,
                install_tool_dependencies=install_tool_dependencies,
                repo_info_dicts=filtered_repos,
                shed_tool_conf=tool_configuration,
                tool_path=tool_path,
                tool_panel_section_keys=tool_panel_keys)
            tool_shed_repositories = irm.install_repositories(
                tsr_ids=encoded_repository_ids,
                decoded_kwd=decoded_kwd,
                reinstalling=False)
            return { 'message': 'Success.' }
        else:
            raise Exception('Repository ids missing.')

    def _get_repo_info_dict(self, trans, repositories, tool_shed_url):
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
    def uninstall(self, trans, payload={}, **kwd):
        """
        DELETE /api/repositories/
        :param payload: name: Repository name
                        author: Repository author
                        changeset_revision : Changeset revision to uninstall
                        tool_shed_url : Toolshed url
                        remove_from_disk : Remove repository from disk or deactivate repository (optional).
        """
        name = payload.get('name')
        owner = payload.get('owner')
        tool_shed = util.remove_protocol_from_url(payload.get('tool_shed_url'))
        changeset_revision = payload.get('changeset_revision')
        if None in [name, owner, tool_shed, changeset_revision]:
            raise Exception('Parameters missing, requires name, owner, tool_shed and changeset_revision.')
        repository = self.app.tool_shed_repository_cache.get_installed_repository(tool_shed=tool_shed, name=name, owner=owner, changeset_revision=changeset_revision)
        if not repository:
            raise Exception('Repository not found')
        irm = InstalledRepositoryManager(app=self.app)
        remove_from_disk = payload.get('remove_from_disk', True)
        errors = irm.uninstall_repository(repository=repository, remove_from_disk=remove_from_disk)
        if not errors:
            action = 'removed' if remove_from_disk else 'disabled'
            return {'message': 'The repository named %s has been %s.' % (repository.name, action)}
        else:
            raise Exception('Attempting to uninstall repository %s resulted in errors: %s' % (repository.name, errors))

    @expose_api
    @web.require_admin
    def search(self, trans, tool_shed_url, **params):
        """
        GET /api/repositories/search
        Search for a specific repository in the toolshed.
        :param q: the query string to search for
        :param q: str
        :param tool_shed_url: the URL of the toolshed to search
        :param tool_shed_url: str
        """
        response = json.loads(util.url_get(tool_shed_url, params=dict(params), pathspec=['api', 'repositories']))
        return response

    @expose_api
    @web.require_admin
    def categories(self, trans, tool_shed_url):
        """
        GET /api/repositories/categories
        List all available categories
        :param tool_shed_url: the URL of the toolshed to search
        :param tool_shed_url: str
        """
        response = json.loads(util.url_get(tool_shed_url, pathspec=['api', 'categories']))
        return response

    @expose_api
    @web.require_admin
    def details(self, trans, tool_shed_url, repository_id):
        """
        GET /api/repositories/details
        :param id: encoded repository id
        :param id: str
        Return details for a given repository id
        """
        response = json.loads(util.url_get(tool_shed_url, pathspec=['api', 'repositories', repository_id, 'metadata']))
        return response
