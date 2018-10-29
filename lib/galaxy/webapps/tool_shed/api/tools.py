import json
import logging
from collections import namedtuple

from galaxy import (
    exceptions,
    util,
    web
)
from galaxy.tools.parameters import params_to_strings
from galaxy.tools.repositories import ValidationContext
from galaxy.web import _future_expose_api_raw_anonymous_and_sessionless as expose_api_raw_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController
from galaxy.webapps.tool_shed.search.tool_search import ToolSearch
from tool_shed.dependencies.repository import relation_builder
from tool_shed.tools import tool_validator
from tool_shed.util import (
    common_util,
    metadata_util,
    repository_util,
    shed_util_common as suc
)
from tool_shed.utility_containers import ToolShedUtilityContainerManager

log = logging.getLogger(__name__)


class ToolsController(BaseAPIController):
    """RESTful controller for interactions with tools in the Tool Shed."""

    @expose_api_raw_anonymous_and_sessionless
    def index(self, trans, **kwd):
        """
        GET /api/tools
        Displays a collection of tools with optional criteria.

        :param q:        (optional)if present search on the given query will be performed
        :type  q:        str

        :param page:     (optional)requested page of the search
        :type  page:     int

        :param page_size:     (optional)requested page_size of the search
        :type  page_size:     int

        :param jsonp:    (optional)flag whether to use jsonp format response, defaults to False
        :type  jsonp:    bool

        :param callback: (optional)name of the function to wrap callback in
                         used only when jsonp is true, defaults to 'callback'
        :type  callback: str

        :returns dict:   object containing list of results and metadata

        Examples:
            GET http://localhost:9009/api/tools
            GET http://localhost:9009/api/tools?q=fastq
        """
        q = kwd.get('q', '')
        if not q:
            raise exceptions.NotImplemented('Listing of all the tools is not implemented. Provide parameter "q" to search instead.')
        else:
            page = kwd.get('page', 1)
            page_size = kwd.get('page_size', 10)
            try:
                page = int(page)
                page_size = int(page_size)
            except ValueError:
                raise exceptions.RequestParameterInvalidException('The "page" and "page_size" have to be integers.')
            return_jsonp = util.asbool(kwd.get('jsonp', False))
            callback = kwd.get('callback', 'callback')
            search_results = self._search(trans, q, page, page_size)
            if return_jsonp:
                response = str('%s(%s);' % (callback, json.dumps(search_results)))
            else:
                response = json.dumps(search_results)
            return response

    def _search(self, trans, q, page=1, page_size=10):
        """
        Perform the search over TS tools index.
        Note that search works over the Whoosh index which you have
        to pre-create with scripts/tool_shed/build_ts_whoosh_index.sh manually.
        Also TS config option toolshed_search_on has to be True and
        whoosh_index_dir has to be specified.
        """
        conf = self.app.config
        if not conf.toolshed_search_on:
            raise exceptions.ConfigDoesNotAllowException('Searching the TS through the API is turned off for this instance.')
        if not conf.whoosh_index_dir:
            raise exceptions.ConfigDoesNotAllowException('There is no directory for the search index specified. Please contact the administrator.')
        search_term = q.strip()
        if len(search_term) < 3:
            raise exceptions.RequestParameterInvalidException('The search term has to be at least 3 characters long.')

        tool_search = ToolSearch()

        Boosts = namedtuple('Boosts', ['tool_name_boost',
                                       'tool_description_boost',
                                       'tool_help_boost',
                                       'tool_repo_owner_username_boost'])
        boosts = Boosts(float(conf.get('tool_name_boost', 1.2)),
                        float(conf.get('tool_description_boost', 0.6)),
                        float(conf.get('tool_help_boost', 0.4)),
                        float(conf.get('tool_repo_owner_username_boost', 0.3)))

        results = tool_search.search(trans,
                                     search_term,
                                     page,
                                     page_size,
                                     boosts)
        results['hostname'] = web.url_for('/', qualified=True)
        return results

    @expose_api_raw_anonymous_and_sessionless
    def json(self, trans, **kwd):
        """
        GET /api/tools/json

        Get the tool form JSON for a tool in a repository.

        :param guid:          the GUID of the tool
        :param guid:          str

        :param tsr_id:        the ID of the repository
        :param tsr_id:        str

        :param changeset:     the changeset at which to load the tool json
        :param changeset:     str
        """
        guid = kwd.get('guid', None)
        tsr_id = kwd.get('tsr_id', None)
        changeset = kwd.get('changeset', None)
        if None in [changeset, tsr_id, guid]:
            message = 'Changeset, repository ID, and tool GUID are all required parameters.'
            trans.response.status = 400
            return {'status': 'error', 'message': message}
        tsucm = ToolShedUtilityContainerManager(trans.app)
        repository = repository_util.get_repository_in_tool_shed(self.app, tsr_id)
        repository_clone_url = common_util.generate_clone_url_for_repository_in_tool_shed(repository.user, repository)
        repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision(trans.app, tsr_id, changeset)
        toolshed_base_url = str(web.url_for('/', qualified=True)).rstrip('/')
        rb = relation_builder.RelationBuilder(trans.app, repository, repository_metadata, toolshed_base_url)
        repository_dependencies = rb.get_repository_dependencies_for_changeset_revision()
        containers_dict = tsucm.build_repository_containers(repository,
                                                            changeset,
                                                            repository_dependencies,
                                                            repository_metadata)
        found_tool = None
        for folder in containers_dict['valid_tools'].folders:
            if hasattr(folder, 'valid_tools'):
                for tool in folder.valid_tools:
                    tool.id = tool.tool_id
                    tool_guid = suc.generate_tool_guid(repository_clone_url, tool)
                    if tool_guid == guid:
                        found_tool = tool
                        break
        if found_tool is None:
            message = 'Unable to find tool with guid %s in repository %s.' % (guid, repository.name)
            trans.response.status = 404
            return {'status': 'error', 'message': message}

        with ValidationContext.from_app(trans.app) as validation_context:
            tv = tool_validator.ToolValidator(validation_context)
            repository, tool, valid, message = tv.load_tool_from_changeset_revision(tsr_id,
                                                                                    changeset,
                                                                                    found_tool.tool_config)
        if message or not valid:
            status = 'error'
            return dict(message=message, status=status)
        tool_help = ''
        if tool.help:
            tool_help = tool.help.render(static_path=web.url_for('/static'), host_url=web.url_for('/', qualified=True))
            tool_help = util.unicodify(tool_help, 'utf-8')
        tool_dict = tool.to_dict(trans)
        tool_dict['inputs'] = {}
        tool.populate_model(trans, tool.inputs, {}, tool_dict['inputs'])
        tool_dict.update({
            'help'          : tool_help,
            'citations'     : bool(tool.citations),
            'biostar_url'   : trans.app.config.biostar_url,
            'requirements'  : [{'name' : r.name, 'version' : r.version} for r in tool.requirements],
            'state_inputs'  : params_to_strings(tool.inputs, {}, trans.app),
            'display'       : tool.display_interface,
            'action'        : web.url_for(tool.action),
            'method'        : tool.method,
            'enctype'       : tool.enctype
        })
        return json.dumps(tool_dict)
