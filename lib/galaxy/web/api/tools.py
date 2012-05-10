from galaxy import config, tools, web, util
from galaxy.web.base.controller import BaseController, BaseAPIController
from galaxy.util.bunch import Bunch

messages = Bunch(
    NO_TOOL = "no tool"
)

class ToolsController( BaseAPIController ):
    """
    RESTful controller for interactions with tools.
    """
    
    @web.expose_api
    def index( self, trans, **kwds ):
        """
        GET /api/tools: returns a list of tools defined by parameters
            parameters:
                in_panel  - if true, tools are returned in panel structure, 
                            including sections and labels
                trackster - if true, only tools that are compatible with 
                            Trackster are returned
        """
        
        # Read params.
        in_panel = util.string_as_bool( kwds.get( 'in_panel', 'True' ) )
        trackster = util.string_as_bool( kwds.get( 'trackster', 'False' ) )
        
        # Create return value.
        return self.app.toolbox.to_dict( trans, in_panel=in_panel, trackster=trackster )

    @web.json
    def show( self, trans, id, **kwd ):
        """
        GET /api/tools/{tool_id}
        Returns tool information, including parameters and inputs.
        """
        return self.app.toolbox.tools_by_id[ id ].to_dict( trans, for_display=True )
        
    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/tools
        Executes tool using specified inputs, creating new history-dataset 
        associations, which are returned.
        """
        
        # TODO: set target history?
        
        # -- Execute tool. --
        
        # Get tool.
        tool_id = payload[ 'id' ]
        tool = trans.app.toolbox.get_tool( tool_id )
        if not tool:
            return { "message": { "type": "error", "text" : messages.NO_TOOL } }
        
        # Set up inputs.
        inputs = payload[ 'inputs' ]
        # HACK: add run button so that tool.handle_input will run tool.
        inputs['runtool_btn'] = 'Execute'
        # TODO: encode data ids and decode ids.
        params = util.Params( inputs, sanitize = False )
        template, vars = tool.handle_input( trans, params.__dict__ )
        
        # TODO: check for errors and ensure that output dataset(s) are available.
        output_datasets = vars[ 'out_data' ].values()
        rval = {
            "outputs": []
        }
        outputs = rval[ "outputs" ]
        for output in output_datasets:
            outputs.append( output.get_api_value() )
        return rval
        