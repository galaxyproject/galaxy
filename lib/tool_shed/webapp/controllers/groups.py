import logging

from galaxy import web
from galaxy.webapps.base.controller import BaseUIController

log = logging.getLogger(__name__)


class Group(BaseUIController):
    @web.expose
    def index(self, trans, **kwd):
        # define app configuration for generic mako template
        app = {"jscript": "../toolshed/scripts/toolshed.groups"}
        return trans.fill_template(
            "/webapps/tool_shed/group/index.mako", config={"title": "Tool Shed Groups", "app": app}
        )
