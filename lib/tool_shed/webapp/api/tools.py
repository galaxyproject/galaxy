import json
import logging

from galaxy import (
    exceptions,
    util,
)
from galaxy.web import (
    expose_api,
    expose_api_raw_anonymous_and_sessionless,
    require_admin,
)
from tool_shed.managers.tools import search
from tool_shed.util.shed_index import build_index
from . import BaseShedAPIController

log = logging.getLogger(__name__)


class ToolsController(BaseShedAPIController):
    """RESTful controller for interactions with tools in the Tool Shed."""

    @expose_api
    @require_admin
    def build_search_index(self, trans, **kwd):
        """
        PUT /api/tools/build_search_index

        Not part of the stable API, just something to simplify bootstrapping tool sheds,
        scripting, testing, etc...
        """
        repos_indexed, tools_indexed = build_index(
            trans.app.config.whoosh_index_dir,
            trans.app.config.file_path,
            trans.app.config.hgweb_config_dir,
            trans.app.config.hgweb_repo_prefix,
            trans.app.config.database_connection,
        )
        return {
            "repositories_indexed": repos_indexed,
            "tools_indexed": tools_indexed,
        }

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
        q = kwd.get("q", "")
        if not q:
            raise exceptions.NotImplemented(
                'Listing of all the tools is not implemented. Provide parameter "q" to search instead.'
            )
        else:
            page = kwd.get("page", 1)
            page_size = kwd.get("page_size", 10)
            try:
                page = int(page)
                page_size = int(page_size)
            except ValueError:
                raise exceptions.RequestParameterInvalidException('The "page" and "page_size" have to be integers.')
            return_jsonp = util.asbool(kwd.get("jsonp", False))
            callback = kwd.get("callback", "callback")
            search_results = search(trans, q, page, page_size)
            if return_jsonp:
                response = str(f"{callback}({json.dumps(search_results)});")
            else:
                response = json.dumps(search_results)
            return response
