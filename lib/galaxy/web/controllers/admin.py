
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
        users, data = [], []
        ut = trans.model.User.table
        dt = trans.model.Dataset.table
        for row in ut.select().execute():
            users.append( row )
        for row in dt.select().execute():
            data.append( row )
        qsize = self.app.job_queue.queue.qsize() 
        return trans.fill_template('admin_main.tmpl', toolbox=self.app.toolbox, users=users, data=data, qsize=qsize,msg=msg)

    def tool_reload( self, tool_version=None, **kwd ):
        params = util.Params( kwd )
        if params.passwd==self.app.config.admin_pass:
            tool_id = params.tool_id
            self.app.toolbox.reload( tool_id )
            msg = 'Reloaded tool: ' + tool_id
        else:
            msg = 'Invalid password'
        return msg

    def update_metadata( self, **kwd ):
        pass
