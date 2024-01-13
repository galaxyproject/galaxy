from tool_shed.structured_app import ToolShedApp

from galaxy.webapps.base.controller import BaseAPIController


class BaseShedAPIController(BaseAPIController):
    app: ToolShedApp

    def __init__(self, app: ToolShedApp):
        super().__init__(app)
