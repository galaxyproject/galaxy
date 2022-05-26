"""API key retrieval through BaseAuth

Sample usage

.. code-block::

    curl --user zipzap@foo.com:password http://localhost:8080/api/authenticate/baseauth

Returns

.. code-block:: json

    {
        "api_key": "baa4d6e3a156d3033f05736255f195f9"
    }

"""
from galaxy.web import expose_api_anonymous_and_sessionless
from galaxy.webapps.base.webapp import GalaxyWebTransaction
from galaxy.webapps.galaxy.services.authenticate import (
    APIKeyResponse,
    AuthenticationService,
)
from . import (
    BaseGalaxyAPIController,
    depends,
)


class AuthenticationController(BaseGalaxyAPIController):
    authentication_service = depends(AuthenticationService)

    @expose_api_anonymous_and_sessionless
    def options(self, trans: GalaxyWebTransaction, **kwd):
        """
        A no-op endpoint to return generic OPTIONS for the API.
        Any OPTIONS request to /api/* maps here.
        Right now this is solely to inform preflight CORS checks, which are API wide.
        Might be better placed elsewhere, but for now this is the initial entrypoint for relevant consumers.
        """
        trans.response.headers["Access-Control-Allow-Headers"] = "*"
        trans.response.headers["Access-Control-Max-Age"] = 600
        # No need to set allow-methods for preflight cors check, I don't think.
        # When this is actually granular, endpoints should *probably* respond appropriately.
        # trans.response.headers['Access-Control-Allow-Methods'] = 'POST, PUT, GET, OPTIONS, DELETE'

    @expose_api_anonymous_and_sessionless
    def get_api_key(self, trans: GalaxyWebTransaction, **kwd) -> APIKeyResponse:
        """
        GET /api/authenticate/baseauth
          returns an API key for authenticated user based on BaseAuth headers

        :returns: api_key in json format
        :rtype:   dict

        :raises: ObjectNotFound, HTTPBadRequest
        """
        return self.authentication_service.get_api_key(trans.environ)
