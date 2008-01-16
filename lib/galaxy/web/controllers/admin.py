
from galaxy.web.base.controller import *
import logging, sets, time

log = logging.getLogger( __name__ )

class Admin( BaseController ):
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
        ut = trans.model.User.table
        dt = trans.model.Dataset.table
        for row in ut.select().execute():
            users.append( row )
        for row in dt.select().execute():
            data.append( row )
        qsize = self.app.job_queue.queue.qsize() 
        return trans.fill_template('admin_main.tmpl', toolbox=self.app.toolbox, users=users, data=data, qsize=qsize,msg=msg)
        
    def abandon( self, **kwd ):
        """
        'Abandons' userless histories older than the specified number of days by setting the 'deleted'
        column to 't' in the History table for each History.id whose History.user_id column is null.
        A list of each of the affected history records is generated during the process.  This list is
        then used to find all undeleted datasets that are associated with these histories.  Each of
        these datasets is then deleted by setting the Dataset.deleted column to 't'.  Nothing is removed
        from the file system.  This function should be executed in preparation for purging datasets using 
        the purge() function below.
        """
        params = util.Params(kwd)
        msg = ''
        if params.abandon_days:
            if params.passwd==self.app.config.admin_pass:
                days = int(params.abandon_days)
                histories_no_users = []
                history_count = 0
                ht = self.app.model.History.table
                for row in ht.select( ht.c.user_id==None ).execute():
                    now  = time.time()
                    last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
                    diff = (now-last)/3600/24 # days
                    if diff > days:
                        histories_no_users.append( row.id )
                        if not row.deleted:
                            log.warn( "Updating history table, setting id %s to deleted" %str( row.id ) )
                            history = self.app.model.History.get( row.id )
                            history.deleted = True
                            history_count += 1
                dataset_count = 0
                dt = self.app.model.Dataset.table
                for row in dt.select( dt.c.deleted=='f' ).execute():
                    if row.history_id in histories_no_users:
                        log.warn( "Updating dataset table, setting id %s to deleted" %str( row.id ) )
                        data = self.app.model.Dataset.get( row.id )
                        data.deleted = True
                        dataset_count += 1
                try:
                    self.app.model.flush()
                except:
                    pass
                msg = 'Deleted %d histories (including a total of %d datasets )' % ( history_count, dataset_count )
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
                now = time.time()
                dt = self.app.model.Dataset.table
                for row in dt.select( ( dt.c.purged=='f' ) & ( dt.c.deleted=='t' ) ).execute():
                    last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) )
                    diff = (now-last)/3600/24 # days
                    if diff > days:
                        log.warn( "Purging dataset id %s" %str( row.id ) )
                        data = app.model.Dataset.get( row.id )
                        data.purge()
                        data.flush()
                        count += 1
                try:
                    self.app.model.flush()
                except:
                    pass
                msg = 'purged %d datasets' % count
            else:
                msg = 'Invalid password'
        return msg

    def tool_reload( self, **kwd ):
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
