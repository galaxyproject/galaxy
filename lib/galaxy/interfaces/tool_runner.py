"""
Upload class

"""

from galaxy import util, web
import common
import logging

log = logging.getLogger( __name__ )

class ToolRunner(common.Root):

    #Hack to get biomart to work, ideally, we could pass tool_id to biomart and receive it back
    @web.expose
    def biomart(self, trans, tool_id='biomart', **kwd):
        """Catches the tool id and redirects as needed"""
        return self.index(trans, tool_id=tool_id, **kwd)

    @web.expose
    def default(self, trans, tool_id=None, **kwd):
        """Catches the tool id and redirects as needed"""
        return self.index(trans, tool_id=tool_id, **kwd)

    @web.expose
    def index(self, trans, tool_id=None, **kwd):
        # No tool id passed, redirect to main page
        if tool_id is None:
            return trans.response.send_redirect( "/static/welcome.html" )
        # Load the tool
        toolbox = self.get_toolbox()
        tool = toolbox.tools_by_id.get( tool_id, None )
        # No tool matching the tool id, display an error (shouldn't happen)
        if not tool:
            log.error( "index called with tool id '%s' but no such tool exists", tool_id )
            trans.log_event( "Tool id '%s' does not exist" % tool_id )
            return "Tool '%s' does not exist, kwd=%s " % (tool_id, kwd)
        params = util.Params(kwd)
        history = trans.get_history()
        trans.ensure_valid_galaxy_session()
        template, vars = tool.handle_input( trans, params.__dict__ )
        trans.log_event( "Tool View: %s; %s" % (str(tool),str(params)), tool_id=tool_id )
        return trans.fill_template( template, history=history, toolbox=toolbox, tool=tool, util=util, **vars )