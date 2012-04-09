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
                trackster - if true, only tools that are compatible with Trackster are returned
        """
        
        # Read params.
        in_panel = util.string_as_bool( kwds.get( 'in_panel', 'True' ) )
        trackster = util.string_as_bool( kwds.get( 'trackster', 'False' ) )
        
        # Create return value.
        return self.app.toolbox.to_dict( trans, in_panel=in_panel, trackster=trackster )
        