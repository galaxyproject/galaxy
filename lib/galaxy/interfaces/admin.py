import logging, sets, time

from galaxy import util, datatypes, jobs, web, config
import common

log = logging.getLogger( __name__ )

class Admin( common.Root ):
    @web.expose
    def index( self, trans, **kwd ):
        msg = ''
        
        if 'action' in kwd:
            if kwd['action'] == "delete":
                msg = self.delete( **kwd )
            elif kwd['action'] == "tool_reload":
                msg = self.tool_reload( **kwd )
        
        users, data = [], []
        for row in trans.model.User.table.select().execute():
            users.append(row)
        for row in trans.model.Dataset.table.select().execute():
            data.append(row)
        
        qsize = self.app.job_queue.queue.qsize() 
        return trans.fill_template('admin_main.tmpl', toolbox=self.app.toolbox, users=users, data=data, qsize=qsize,msg=msg)
        
    def delete( self, **kwd ):
        params = util.Params(kwd)
        msg = ''
        if params.days:
            if params.passwd==self.app.config.admin_pass:
                days = int(params.days)
                values = []
                for row in self.app.model.Dataset.table.select().execute():
                    values.append(self.app.model.Dataset.get(row.id))
                for row in self.app.model.History.table.select().execute():
                    values.append(self.app.model.History.get(row.id))
                #for row in self.app.model.User.table.select().execute():
                #    values.append(self.app.model.User.get(row.id))
                count = 0
                for value in values:
                    now  = time.time()
                    last = time.mktime( time.strptime( value.update_time.strftime('%a %b %d %H:%M:%S %Y') ))
                    diff = (now - last) /3600/24 # days
                    if diff>days:
                        #value.delete()
                        value.deleted = True
                        count += 1
                try:
                    self.app.model.flush()
                except:
                    pass
                msg = 'Deleted %d objects' % count
            else:
                msg = 'Invalid password'
        return msg

    def tool_reload( self, **kwd ):
        params = util.Params(kwd)
        if params.passwd==self.app.config.admin_pass:
            tool_id = params.tool_id
            self.app.toolbox.reload( tool_id )
            msg = 'Reloaded tool: ' + tool_id
        else:
            msg = 'Invalid password'
        return msg

