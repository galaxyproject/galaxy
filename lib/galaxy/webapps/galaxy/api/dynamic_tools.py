from galaxy import web, util
from galaxy.exceptions import ObjectNotFound
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous_and_sessionless as expose_api_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController


import logging
log = logging.getLogger(__name__)


class DynamicToolsController(BaseAPIController):
    """
    RESTful controller for interactions with dynamic tools.

    Dynamic tools are tools defined in the database. Use the tools controller
    to run these tools and view functional information.
    """

    def __init__(self, app):
        super(DynamicToolsController, self).__init__(app)

    @expose_api_anonymous_and_sessionless
    def index(self, trans, **kwds):
        """
        GET /api/dynamic_tools: returns a list of dynamic tools.

        This returns meta-information about the dynamic tool, such as
        tool_hash. To use the tool or view funtional information such as
        inputs and outputs, use the standard tools API indexed by the
        ID (and optionally version) returned from this endpoint.
        """
        manager = self.app.dynamic_tools_manager
        return list(
            map(lambda t: t.to_dict(), manager.list_tools())
        )

    @expose_api_anonymous_and_sessionless
    def show(self, trans, id, **kwd):
        """
        GET /api/dynamic_tools/{tool_id|tool_hash|uuid}
        """
        manager = self.app.dynamic_tools_manager
        if util.is_uuid(id):
            dynamic_tool = manager.get_by_uuid(id)
        else:
            dynamic_tool = manager.get_by_id_or_hash(id)
        if dynamic_tool is None:
            raise ObjectNotFound()

        return dynamic_tool.to_dict()

    @web.require_admin
    @expose_api
    def create(self, trans, payload, **kwd):
        """
        POST /api/dynamic_tools

        If ``tool_id`` appears in the payload this executes tool using
        specified inputs and returns tool's outputs. Otherwise, the payload
        is expected to be a tool definition to dynamically load into Galaxy's
        toolbox.
        """
        dynamic_tool = self.app.dynamic_tools_manager.create_tool(
            payload
        )
        return dynamic_tool.to_dict()
