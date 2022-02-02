"""
API key retrieval through BaseAuth
Sample usage:

.. code-block::

    curl --user zipzap@foo.com:password http://localhost:9009/api/authenticate/baseauth

Returns

.. code-block:: json

    {
        "api_key": "<some api key>"
    }

"""
import logging

from galaxy.web import expose_api_raw_anonymous_and_sessionless
from galaxy.webapps.galaxy.api.authenticate import AuthenticationController

log = logging.getLogger(__name__)


class ToolShedAuthenticationController(AuthenticationController):
    @expose_api_raw_anonymous_and_sessionless
    def get_tool_shed_api_key(self, trans, **kwd):
        """
        GET /api/authenticate/baseauth

        returns an API key for authenticated user based on BaseAuth headers

        :returns: api_key in json format
        :rtype:   dict

        :raises: ObjectNotFound, HTTPBadRequest
        """
        return self.get_api_key(trans, **kwd)
