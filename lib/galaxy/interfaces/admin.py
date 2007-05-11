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
            elif kwd['action'] == "purge":
                msg = self.purge( **kwd )
            elif kwd['action'] == "abandon":
                msg = self.abandon( **kwd )
        
        users, data = [], []
        for row in trans.model.User.table.select().execute():
            users.append(row)
        for row in trans.model.Dataset.table.select().execute():
            data.append(row)
        
        qsize = self.app.job_queue.queue.qsize() 
        return trans.fill_template('admin_main.tmpl', toolbox=self.app.toolbox, users=users, data=data, qsize=qsize,msg=msg)
        
    
    def abandon( self, **kwd ):
        params = util.Params(kwd)
        msg = ''
        if params.days:
            if params.passwd==self.app.config.admin_pass:
                days = int(params.abandon_days)
                
                histories_no_users = []
                history_count = 0
                for row in self.app.model.History.table.select().execute():
                    try:
                        int(row.user_id)
                    except:
                        history = self.app.model.History.get(row.id)
                        now  = time.time()
                        last = time.mktime( time.strptime( history.update_time.strftime('%a %b %d %H:%M:%S %Y') )) 
                        diff = (now - last) /3600/24 # days
                        if diff>days:
                            histories_no_users.append(row.id)
                            if history.deleted: continue #we don't add to history delete count, but we do want to be able to make sure datasets associated with deleted histories are really deleted
                            history.deleted = True
                            history_count += 1
                
                dataset_count = 0
                for row in self.app.model.Dataset.table.select().execute():
                    if row.history_id in histories_no_users:
                        #delete dataset
                        data = self.app.model.Dataset.get(row.id)
                        if data.deleted: continue
                        data.deleted = True
                        dataset_count += 1
                try:
                    self.app.model.flush()
                except:
                    pass
                msg = 'deleted %d abandoned histories with %d total datasets' % ( history_count, dataset_count )
            else:
                msg = 'Invalid password'
        return msg
    
    def purge( self, **kwd ):
        """ Purges deleted datasets older than specified number of days """
        params = util.Params(kwd)
        msg = ''
        if params.purge_days:
            if params.passwd==self.app.config.admin_pass:
                days = int(params.purge_days)
                count = 0
                now  = time.time()
                for row in self.app.model.Dataset.table.select().execute():
                    data = self.app.model.Dataset.get(row.id)
                    if data.deleted and not data.purged:
                        last = time.mktime( time.strptime( data.update_time.strftime('%a %b %d %H:%M:%S %Y') ))
                        diff = (now - last) /3600/24 # days
                        if diff>days:
                            data.purge()
                            count += 1
                try:
                    self.app.model.flush()
                except:
                    pass
                msg = 'Purged %d datasets' % count
            else:
                msg = 'Invalid password'
        return msg
    
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

