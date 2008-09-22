"""
Upload class
"""

from galaxy.web.base.controller import *

import logging
log = logging.getLogger( __name__ )

class AddFrameData:
    def __init__( self ):
        self.wiki_url = None
        self.debug = None
        self.from_noframe = None

class ToolRunner( BaseController ):

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
    def index(self, trans, tool_id=None, from_noframe=None, **kwd):
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
        params = util.Params(kwd, sanitize = tool.options.sanitize)
        history = trans.get_history()
        trans.ensure_valid_galaxy_session()
        template, vars = tool.handle_input( trans, params.__dict__ )
        if len(params) > 0:
            trans.log_event( "Tool params: %s" % (str(params)), tool_id=tool_id )
        add_frame = AddFrameData()
        add_frame.debug = trans.debug
        if from_noframe is not None:
            add_frame.wiki_url = trans.app.config.wiki_url
            add_frame.from_noframe = True
        return trans.fill_template( template, history=history, toolbox=toolbox, tool=tool, util=util, add_frame=add_frame, **vars )

    @web.expose
    def redirect( self, trans, redirect_url=None, **kwd ):
        if not redirect_url:
            return trans.show_error_message( "Required URL for redirection missing" )
        trans.log_event( "Redirecting to: %s" % redirect_url )
        return trans.fill_template( 'root/redirect.mako', redirect_url=redirect_url )
