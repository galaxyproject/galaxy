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

from galaxy.web import expose_api_anonymous_and_sessionless
from galaxy.webapps.galaxy.api import depends
from galaxy.webapps.galaxy.services.authenticate import AuthenticationService
from . import BaseShedAPIController

log = logging.getLogger(__name__)


class ToolShedAuthenticationController(BaseShedAPIController):
    authentication_service = depends(AuthenticationService)

    @expose_api_anonymous_and_sessionless
    def get_tool_shed_api_key(self, trans, **kwd):
        """
        GET /api/authenticate/baseauth

        returns an API key for authenticated user based on BaseAuth headers

        :returns: api_key in json format
        :rtype:   dict

        :raises: ObjectNotFound, HTTPBadRequest
        """
        return self.authentication_service.get_api_key(trans.environ, trans.request)
