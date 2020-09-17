"""Proxy requests to GA4GH TRS servers (e.g. Dockstore).

Information on TRS can be found at https://github.com/ga4gh/tool-registry-service-schemas.
"""
from galaxy.web import expose_api
from galaxy.webapps.base.controller import (
    BaseAPIController
)


class TrsConsumeAPIController(BaseAPIController):
    """Controller for TRS proxying."""

    def __init__(self, app):
        self._trs_proxy = app.trs_proxy

    @expose_api
    def get_servers(self, trans, *args, **kwd):
        return self._trs_proxy.get_servers()

    @expose_api
    def get_tool(self, trans, *args, **kwd):
        return self._trs_proxy.get_tool(*args, **kwd)

    @expose_api
    def get_versions(self, trans, *args, **kwd):
        return self._trs_proxy.get_versions(*args, **kwd)

    @expose_api
    def get_version(self, trans, *args, **kwd):
        return self._trs_proxy.get_version(*args, **kwd)
