from galaxy import config, tools, web, util
from galaxy.web.base.controller import BaseController, BaseUIController

class ToolsController( BaseUIController ):
    """
    RESTful controller for interactions with tools. Once session-based 
    authentication can be done with API controllers, this will be moved
    to be part of the API.
    """
    
    @web.json
    def index( self, trans, **kwds ):
        """
        GET /api/tools: returns a list of tools defined by parameters
            parameters: 
                in_panel - if true, tools are returned in panel structure, including sections and labels
        """
        in_panel = util.string_as_bool( kwds.get( 'in_panel', 'True' ) )
        if in_panel:
            panel_elts = []
            # Taken from tool_menu.mako:
            for key, val in self.app.toolbox.tool_panel.items():
                panel_elts.append( val.to_dict( trans ) )
            rval = panel_elts
        else:
            tools = []
            for id, tool in self.app.toolbox.tools_by_id.items():
                tools.append( tool.to_dict( trans ) )
            rval = tools

        return rval
        