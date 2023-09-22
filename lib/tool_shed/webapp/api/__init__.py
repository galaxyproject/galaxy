from galaxy.webapps.base.controller import BaseAPIController
from tool_shed.structured_app import ToolShedApp


class BaseShedAPIController(BaseAPIController):
    app: ToolShedApp

    def __init__(self, app: ToolShedApp):
        super().__init__(app)
