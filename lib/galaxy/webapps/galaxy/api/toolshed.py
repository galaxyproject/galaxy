import json
import logging
import re

from six.moves.urllib.parse import (
    quote as urlquote,
    unquote as urlunquote
)

from galaxy import (
    util,
    web
)
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import BaseAPIController
from tool_shed.util import (
    common_util,
    repository_util,
    tool_util
)

log = logging.getLogger(__name__)


class ToolShedController(BaseAPIController):
    """RESTful controller for interactions with tool sheds."""

    def __get_repo_dict_by_id(self, id):
        tool_shed_repository = repository_util.get_tool_shed_repository_by_id(self.app, id)
        if tool_shed_repository is None:
            log.debug("Unable to locate tool_shed_repository record for id %s." % (str(id)))
            return {}
        tool_shed_repository_dict = tool_shed_repository.as_dict(value_mapper=self.__get_value_mapper(tool_shed_repository))
        tool_shed_repository_dict['url'] = web.url_for(controller='tool_shed_repositories',
                                                       action='show',
                                                       id=self.app.security.encode_id(tool_shed_repository.id))
        tool_shed_repository_dict['repository_dependencies'] = self.__flatten_repository_dependency_list(tool_shed_repository)
        return tool_shed_repository_dict

    def __get_tool_dependencies(self, metadata, tool_dependencies=None):
        if tool_dependencies is None:
            tool_dependencies = []
        if metadata['includes_tool_dependencies']:
            for key, dependency_dict in metadata['tool_dependencies'].items():
                if 'readme' in dependency_dict:
                    del(dependency_dict['readme'])
                if dependency_dict not in tool_dependencies:
                    tool_dependencies.append(dependency_dict)
        if metadata['has_repository_dependencies']:
            for dependency in metadata['repository_dependencies']:
                tool_dependencies = self.__get_tool_dependencies(dependency, tool_dependencies)
        return tool_dependencies

    def __flatten_repository_dependency_list(self, tool_shed_repository):
        '''
        Return a recursive exclusive flattened list of all tool_shed_repository's dependencies.
        '''
        dependencies = []
        for dependency in tool_shed_repository.repository_dependencies:
            if len(dependency.repository_dependencies) > 0:
                sub_dependencies = self.__flatten_repository_dependency_list(dependency)
                for sub_dependency in sub_dependencies:
                    if sub_dependency not in dependencies:
                        dependencies.append(sub_dependency)
            if dependency not in dependencies:
                dependencies.append(dependency.as_dict(value_mapper=self.__get_value_mapper(tool_shed_repository)))
        return dependencies

    def __get_value_mapper(self, tool_shed_repository):
        value_mapper = {'id': self.app.security.encode_id(tool_shed_repository.id),
                        'error_message': tool_shed_repository.error_message or ''}
        return value_mapper

    def __get_tools(self, metadata, tools=None):
        if tools is None:
            tools = []
        if metadata['includes_tools_for_display_in_tool_panel']:
            for key, tool_dict in metadata['tools']:
                tool_info = dict(clean=re.sub('[^a-zA-Z0-9]+', '_', tool_dict['name']).lower(),
                                 name=tool_dict['name'],
                                 version=tool_dict['version'],
                                 description=tool_dict['description'])
                if tool_info not in tools:
                    tools.append(tool_info)
        if metadata['has_repository_dependencies']:
            for dependency in metadata['repository_dependencies']:
                tools = self.__get_tools(dependency, tools)
        return tools

    @expose_api
    def index(self, trans, **kwd):
        """
        GET /api/tool_shed
        Interact with this galaxy instance's toolshed registry.
        """
        sheds = []
        for name, url in trans.app.tool_shed_registry.tool_sheds.items():
            # api_url = web.url_for( controller='api/tool_shed',
            #                        action='contents',
            #                        tool_shed_url=urlquote( url, '' ),
            #                        qualified=True )
            sheds.append(dict(name=name, url=urlquote(url, '')))
        return sheds

    @expose_api
    @web.require_admin
    def status(self, trans, **kwd):
        """
        GET /api/tool_shed_repositories/{id}/status
        Display a dictionary containing information about a specified repository's installation
        status and a list of its dependencies and the status of each.

        :param id: the repository's encoded id
        """
        repository_ids = kwd.get('repositories', None)
        repositories = []
        if repository_ids is not None:
            for repository_id in repository_ids.split('|'):
                tool_shed_repository_dict = self.__get_repo_dict_by_id(repository_id)
                repositories.append(tool_shed_repository_dict)
            return repositories
        else:
            return []
        # return tool_shed_repository_dict

    @expose_api
    @web.require_admin
    def tool_json(self, trans, **kwd):
        """
        GET /api/tool_shed_repositories/shed_tool_json

        Get the tool form JSON for a tool in a toolshed repository.

        :param guid:          the GUID of the tool
        :param guid:          str

        :param tsr_id:        the ID of the repository
        :param tsr_id:        str

        :param changeset:        the changeset at which to load the tool json
        :param changeset:        str

        :param tool_shed_url:   the URL of the toolshed to load from
        :param tool_shed_url:   str
        """
        tool_shed_url = kwd.get('tool_shed_url', None)
        tsr_id = kwd.get('tsr_id', None)
        guid = kwd.get('guid', None)
        changeset = kwd.get('changeset', None)
        if None in [tool_shed_url, tsr_id, guid, changeset]:
            message = 'Tool shed URL, changeset, repository ID, and tool GUID are all required parameters.'
            trans.response.status = 400
            return {'status': 'error', 'message': message}
        response = json.loads(util.url_get(tool_shed_url, params=dict(tsr_id=tsr_id, guid=guid, changeset=changeset.split(':')[-1]), pathspec=['api', 'tools', 'json']))
        return response

    @expose_api
    def show(self, trans, **kwd):
        """
        GET /api/tool_shed/contents

        Display a list of categories in the selected toolshed.

        :param tool_shed_url: the url of the toolshed to get categories from
        """
        tool_shed_url = urlunquote(kwd.get('tool_shed_url', ''))
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(trans.app, tool_shed_url)
        url = util.build_url(tool_shed_url, pathspec=['api', 'categories'])
        categories = []
        for category in json.loads(util.url_get(url)):
            api_url = web.url_for(controller='api/tool_shed',
                                  action='category',
                                  tool_shed_url=urlquote(tool_shed_url),
                                  category_id=category['id'],
                                  qualified=True)
            category['url'] = api_url
            categories.append(category)
        return categories

    @expose_api
    @web.require_admin
    def category(self, trans, **kwd):
        """
        GET /api/tool_shed/category

        Display a list of repositories in the selected category.

        :param tool_shed_url: the url of the toolshed to get repositories from
        :param category_id: the category to get repositories from
        """
        tool_shed_url = urlunquote(kwd.get('tool_shed_url', ''))
        category_id = kwd.get('category_id', '')
        params = dict(installable=True)
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(trans.app, tool_shed_url)
        url = util.build_url(tool_shed_url, pathspec=['api', 'categories', category_id, 'repositories'], params=params)
        repositories = []
        return_json = json.loads(util.url_get(url))
        for repository in return_json['repositories']:
            api_url = web.url_for(controller='api/tool_shed',
                                  action='repository',
                                  tool_shed_url=urlquote(tool_shed_url),
                                  repository_id=repository['id'],
                                  qualified=True)
            repository['url'] = api_url
            repositories.append(repository)
        return_json['repositories'] = repositories
        return return_json

    @expose_api
    def repository(self, trans, **kwd):
        """
        GET /api/tool_shed/repository

        Get details about the specified repository from its shed.

        :param repository_id:          the tool_shed_repository_id
        :param repository_id:          str

        :param tool_shed_url:   the URL of the toolshed whence to retrieve repository details
        :param tool_shed_url:   str

        :param tool_ids:         (optional) comma-separated list of tool IDs
        :param tool_ids:         str
        """
        tool_dependencies = dict()
        tools = dict()
        tool_shed_url = urlunquote(kwd.get('tool_shed_url', ''))
        log.debug(tool_shed_url)
        repository_id = kwd.get('repository_id', None)
        tool_ids = kwd.get('tool_ids', None)
        if tool_ids is not None:
            tool_ids = util.listify(tool_ids)
        tool_panel_section_select_field = tool_util.build_tool_panel_section_select_field(trans.app)
        tool_panel_section_dict = {'name': tool_panel_section_select_field.name,
                                   'id': tool_panel_section_select_field.field_id,
                                   'sections': []}
        for name, id, _ in tool_panel_section_select_field.options:
            tool_panel_section_dict['sections'].append(dict(id=id, name=name))
        repository_data = dict()
        if tool_ids is not None:
            if len(tool_shed_url) == 0:
                # By design, this list should always be from the same toolshed. If
                # this is ever not the case, this code will need to be updated.
                tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(self.app, tool_ids[0].split('/repos')[0])
            found_repository = json.loads(util.url_get(tool_shed_url, params=dict(tool_ids=','.join(tool_ids)), pathspec=['api', 'repositories']))
            current_changeset = found_repository['current_changeset']
            repository_id = found_repository[current_changeset]['repository_id']
            repository_data['current_changeset'] = current_changeset
            repository_data['repository'] = json.loads(util.url_get(tool_shed_url, pathspec=['api', 'repositories', repository_id]))
            del found_repository['current_changeset']
            repository_data['tool_shed_url'] = tool_shed_url
        else:
            repository_data['repository'] = json.loads(util.url_get(tool_shed_url, pathspec=['api', 'repositories', repository_id]))
        repository_data['repository']['metadata'] = json.loads(util.url_get(tool_shed_url, pathspec=['api', 'repositories', repository_id, 'metadata']))
        repository_data['shed_conf'] = tool_util.build_shed_tool_conf_select_field(trans.app).to_dict()
        repository_data['panel_section_dict'] = tool_panel_section_dict
        for changeset, metadata in repository_data['repository']['metadata'].items():
            if changeset not in tool_dependencies:
                tool_dependencies[changeset] = []
            if metadata['includes_tools_for_display_in_tool_panel']:
                if changeset not in tools:
                    tools[changeset] = []
                for tool_dict in metadata['tools']:
                    tool_info = dict(clean=re.sub('[^a-zA-Z0-9]+', '_', tool_dict['name']).lower(),
                                     guid=tool_dict['guid'],
                                     name=tool_dict['name'],
                                     version=tool_dict['version'],
                                     description=tool_dict['description'])
                    if tool_info not in tools[changeset]:
                        tools[changeset].append(tool_info)
                if metadata['has_repository_dependencies']:
                    for repository_dependency in metadata['repository_dependencies']:
                        tools[changeset] = self.__get_tools(repository_dependency, tools[changeset])
            for key, dependency_dict in metadata['tool_dependencies'].items():
                if 'readme' in dependency_dict:
                    del(dependency_dict['readme'])
                if dependency_dict not in tool_dependencies[changeset]:
                    tool_dependencies[changeset].append(dependency_dict)
            if metadata['has_repository_dependencies']:
                for repository_dependency in metadata['repository_dependencies']:
                    tool_dependencies[changeset] = self.__get_tool_dependencies(repository_dependency, tool_dependencies[changeset])
        for changeset in repository_data['repository']['metadata']:
            if changeset in tools:
                repository_data['repository']['metadata'][changeset]['tools'] = tools[changeset]
            else:
                repository_data['repository']['metadata'][changeset]['tools'] = []
        repository_data['tool_dependencies'] = tool_dependencies
        return repository_data

    @expose_api
    @web.require_admin
    def search(self, trans, **kwd):
        """
        GET /api/tool_shed/search
        Search for a specific repository in the toolshed.
        :param q:          the query string to search for
        :param q:          str
        :param tool_shed_url:   the URL of the toolshed to search
        :param tool_shed_url:   str
        """
        tool_shed_url = kwd.get('tool_shed_url', None)
        q = kwd.get('term', None)
        if None in [q, tool_shed_url]:
            return {}
        response = json.loads(util.url_get(tool_shed_url, params=dict(q=q), pathspec=['api', 'repositories']))
        return response
