from galaxy import web, util
from galaxy.web.base.controller import BaseAPIController
from galaxy.tools import global_tool_errors

class ErrorController( BaseAPIController ):
    """
    API methods to obtain error information in different parts of the api.
    """

    @web.expose_api_anonymous
    def index( self, trans, **kwd ):
        """
        GET /api/errors: stub
        """

        return ['tools']

    @web.expose_api
    def tools( self, trans, **kwd ):
        """
        GET /api/errors/tools

        Returns information about stored tool errors
        """
        return global_tool_errors.error_stack

