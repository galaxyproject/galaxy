import json
import logging
from collections import namedtuple

from galaxy import (
    exceptions,
    util,
    web,
)
from galaxy.web import (
    expose_api,
    expose_api_raw_anonymous_and_sessionless,
    require_admin,
)
from galaxy.webapps.base.controller import BaseAPIController
from tool_shed.util.shed_index import build_index
from tool_shed.webapp.search.tool_search import ToolSearch

log = logging.getLogger(__name__)


class ToolsController(BaseAPIController):
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
            search_results = self._search(trans, q, page, page_size)
            if return_jsonp:
                response = str(f"{callback}({json.dumps(search_results)});")
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
            raise exceptions.ConfigDoesNotAllowException(
                "Searching the TS through the API is turned off for this instance."
            )
        if not conf.whoosh_index_dir:
            raise exceptions.ConfigDoesNotAllowException(
                "There is no directory for the search index specified. Please contact the administrator."
            )
        search_term = q.strip()
        if len(search_term) < 1:
            raise exceptions.RequestParameterInvalidException("The search term has to be at least one character long.")

        tool_search = ToolSearch()

        Boosts = namedtuple(
            "Boosts", ["tool_name_boost", "tool_description_boost", "tool_help_boost", "tool_repo_owner_username_boost"]
        )
        boosts = Boosts(
            float(conf.get("tool_name_boost", 1.2)),
            float(conf.get("tool_description_boost", 0.6)),
            float(conf.get("tool_help_boost", 0.4)),
            float(conf.get("tool_repo_owner_username_boost", 0.3)),
        )

        results = tool_search.search(trans, search_term, page, page_size, boosts)
        results["hostname"] = web.url_for("/", qualified=True)
        return results
