import logging

from galaxy import (
    util,
    web,
)
from galaxy.exceptions import ObjectNotFound
from galaxy.web import (
    expose_api,
    expose_api_anonymous_and_sessionless,
)
from galaxy.webapps.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class DynamicToolsController(BaseAPIController):
    """
    RESTful controller for interactions with dynamic tools.

    Dynamic tools are tools defined in the database. Use the tools controller
    to run these tools and view functional information.
    """

    @expose_api_anonymous_and_sessionless
    def index(self, trans, **kwds):
        """
        GET /api/dynamic_tools

        This returns meta-information about the dynamic tool, such as
        tool_uuid. To use the tool or view funtional information such as
        inputs and outputs, use the standard tools API indexed by the
        ID (and optionally version) returned from this endpoint.
        """
        manager = self.app.dynamic_tool_manager
        return [t.to_dict() for t in manager.list_tools()]

    @expose_api_anonymous_and_sessionless
    def show(self, trans, id, **kwd):
        """
        GET /api/dynamic_tools/{encoded_dynamic_tool_id|tool_uuid}
        """
        return self._get_dynamic_tool(trans, id).to_dict()

    @web.require_admin
    @expose_api
    def create(self, trans, payload, **kwd):
        """
        POST /api/dynamic_tools

        The payload is expected to be a tool definition to dynamically load
        into Galaxy's toolbox.

        :type representation: dict
        :param representation: a JSON-ified tool description to load
        :type uuid: str
        :param uuid: the uuid to associate with the tool being created
        """
        dynamic_tool = self.app.dynamic_tool_manager.create_tool(
            trans, payload, allow_load=util.asbool(kwd.get("allow_load", True))
        )
        return dynamic_tool.to_dict()

    @web.require_admin
    @expose_api
    def delete(self, trans, id, **kwd):
        """
        DELETE /api/dynamic_tools/{encoded_dynamic_tool_id|tool_uuid}

        Deactivate the specified dynamic tool. Deactivated tools will not
        be loaded into the toolbox.
        """
        manager = self.app.dynamic_tool_manager
        dynamic_tool = self._get_dynamic_tool(trans, id)
        updated_dynamic_tool = manager.deactivate(dynamic_tool)
        return updated_dynamic_tool.to_dict()

    def _get_dynamic_tool(self, trans, request_id):
        manager = self.app.dynamic_tool_manager
        if util.is_uuid(request_id):
            dynamic_tool = manager.get_tool_by_uuid(request_id)
        else:
            dynamic_tool = manager.get_tool_by_id(trans.security.decode_id(request_id))
        if dynamic_tool is None:
            raise ObjectNotFound()
        return dynamic_tool
