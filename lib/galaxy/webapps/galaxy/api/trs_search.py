"""Proxy requests to GA4GH TRS servers (e.g. Dockstore).

Information on TRS can be found at https://github.com/ga4gh/tool-registry-service-schemas.
"""
import logging

from galaxy.web import expose_api
from galaxy.webapps.base.controller import (
    BaseAPIController
)
from galaxy.workflow.trs_proxy import parse_search_kwds

log = logging.getLogger(__name__)


class TrsSearchAPIController(BaseAPIController):
    """Controller for TRS searching.

    Not trying to emulate the actual underlying GA4GH API interface so throwing
    the search functionality into a different controller than the trs_consumer.
    """

    def __init__(self, app):
        self._trs_proxy = app.trs_proxy

    @expose_api
    def index(self, trans, trs_server=None, query=None, **kwd):
        """
        GET /api/trs_search

        Search a TRS server.

        :param query: search query
        :type  query: str
        """
        search_kwd = parse_search_kwds(query)
        rval = self._trs_proxy.get_tools(trs_server, **search_kwd)
        return rval
