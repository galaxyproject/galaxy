"""Proxy requests to GA4GH TRS servers (e.g. Dockstore).

Information on TRS can be found at https://github.com/ga4gh/tool-registry-service-schemas.
"""
import logging

from galaxy.web import expose_api
from galaxy.workflow.trs_proxy import (
    parse_search_kwds,
    TrsProxy,
)
from . import (
    BaseGalaxyAPIController,
    depends,
)

log = logging.getLogger(__name__)


class TrsSearchAPIController(BaseGalaxyAPIController):
    """Controller for TRS searching.

    Not trying to emulate the actual underlying GA4GH API interface so throwing
    the search functionality into a different controller than the trs_consumer.
    """

    _trs_proxy: TrsProxy = depends(TrsProxy)

    @expose_api
    def index(self, trans, trs_server=None, query=None, **kwd):
        """
        GET /api/trs_search

        Search a TRS server.

        :param query: search query
        :type  query: str
        """
        search_kwd = parse_search_kwds(query)
        rval = self._trs_proxy.get_server(trs_server).get_tools(**search_kwd)
        return rval
