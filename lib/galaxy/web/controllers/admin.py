
from galaxy.web.base.controller import *
import logging, sets, time

log = logging.getLogger( __name__ )

class Admin( BaseController ):
    @web.expose
    def index( self, trans, **kwd ):
        msg = ''
        if 'action' in kwd:
            if kwd['action'] == "tool_reload":
                msg = self.tool_reload( **kwd )
        return trans.fill_template( 'admin_main.mako', toolbox=self.app.toolbox, msg=msg )

    def tool_reload( self, tool_version=None, **kwd ):
        params = util.Params( kwd )
        if params.passwd==self.app.config.admin_pass:
            tool_id = params.tool_id
            self.app.toolbox.reload( tool_id )
            msg = 'Reloaded tool: ' + tool_id
        else:
            msg = 'Invalid password'
        return msg
