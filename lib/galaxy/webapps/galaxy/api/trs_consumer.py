"""Proxy requests to GA4GH TRS servers (e.g. Dockstore).

Information on TRS can be found at https://github.com/ga4gh/tool-registry-service-schemas.
"""
from galaxy.web import expose_api
from galaxy.workflow.trs_proxy import TrsProxy
from . import (
    BaseGalaxyAPIController,
    depends,
)


class TrsConsumeAPIController(BaseGalaxyAPIController):
    """Controller for TRS proxying."""

    _trs_proxy: TrsProxy = depends(TrsProxy)

    @expose_api
    def get_servers(self, trans, *args, **kwd):
        return self._trs_proxy.get_servers()

    @expose_api
    def get_tool(self, trans, payload, **kwd):
        return self._trs_proxy.get_server(payload.get('trs_server')).get_tool(payload.get('tool_id'), **kwd)

    @expose_api
    def get_versions(self, trans, payload, **kwd):
        return self._trs_proxy.get_server(payload.get('trs_server')).get_versions(payload.get('tool_id'), **kwd)

    @expose_api
    def get_version(self, trans, payload, **kwd):
        return self._trs_proxy.get_server(payload.get('trs_server')).get_version(payload.get('tool_id'),
                                                                                 payload.get('version_id'), **kwd)
