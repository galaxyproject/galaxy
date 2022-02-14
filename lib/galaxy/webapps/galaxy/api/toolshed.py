import json
import logging
from urllib.parse import quote

from galaxy.exceptions import MessageException
from galaxy.util import url_get
from galaxy.web import (
    expose_api,
    require_admin,
)
from . import BaseGalaxyAPIController

log = logging.getLogger(__name__)


class ToolShedController(BaseGalaxyAPIController):
    """RESTful controller for interactions with Toolsheds."""

    @expose_api
    def index(self, trans, **kwd):
        """
        GET /api/tool_shed
        Interact with the Toolshed registry of this instance.
        """
        tool_sheds = []
        for name, url in trans.app.tool_shed_registry.tool_sheds.items():
            tool_sheds.append(dict(name=name, url=quote(url, "")))
        return tool_sheds

    @require_admin
    @expose_api
    def request(self, trans, **params):
        """
        GET /api/tool_shed/request
        """
        tool_shed_url = params.pop("tool_shed_url")
        controller = params.pop("controller")
        if controller is None:
            raise MessageException("Please provide a toolshed controller name.")
        tool_shed_registry = trans.app.tool_shed_registry
        if tool_shed_registry is None:
            raise MessageException("Toolshed registry not available.")
        if tool_shed_url in tool_shed_registry.tool_sheds.values():
            pathspec = ["api", controller]
            if "id" in params:
                pathspec.append(params.pop("id"))
            if "action" in params:
                pathspec.append(params.pop("action"))
            try:
                return json.loads(url_get(tool_shed_url, params=dict(params), pathspec=pathspec))
            except Exception as e:
                raise MessageException(f"Invalid server response. {str(e)}.")
        else:
            raise MessageException("Invalid toolshed url.")
