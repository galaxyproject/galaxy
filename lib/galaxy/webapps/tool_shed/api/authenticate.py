"""
API key retrieval through BaseAuth
Sample usage:

curl --user zipzap@foo.com:password http://localhost:9009/api/authenticate/baseauth

Returns:
{
    "api_key": <some api key>
}
"""
import logging

from galaxy.web import _future_expose_api_raw_anonymous_and_sessionless as expose_api_raw_anonymous_and_sessionless
from galaxy.webapps.galaxy.api.authenticate import AuthenticationController

log = logging.getLogger(__name__)


class ToolShedAuthenticationController(AuthenticationController):

    @expose_api_raw_anonymous_and_sessionless
    def get_tool_shed_api_key(self, trans, **kwd):
        """
        def get_api_key( self, trans, **kwd )
        * GET /api/authenticate/baseauth
        returns an API key for authenticated user based on BaseAuth headers

        :returns: api_key in json format
        :rtype:   dict

        :raises: ObjectNotFound, HTTPBadRequest
        """
        return self.get_api_key(trans, **kwd)
