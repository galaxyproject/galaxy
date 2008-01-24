
from galaxy.web.base.controller import *
import logging, sets, time

log = logging.getLogger( __name__ )

class Admin( BaseController ):
    @web.expose
    def index( self, trans, **kwd ):
        msg = ''
        if 'action' in kwd:
            if kwd['action'] == "info_delete_userless_histories":
                msg = self.info_delete_userless_histories( **kwd )
            elif kwd['action'] == "delete_userless_histories":
                msg = self.delete_userless_histories( **kwd )
            elif kwd['action'] == "info_purge_histories":
                msg = self.info_purge_histories( **kwd )
            elif kwd['action'] == "purge_histories":
                msg = self.purge_histories( **kwd )
            elif kwd['action'] == "info_purge_datasets":
                msg = self.info_purge_datasets( **kwd )
            elif kwd['action'] == "purge_datasets":
                msg = self.purge_datasets( **kwd )
            elif kwd['action'] == "info_remove_datasets":
                msg = self.info_remove_datasets( **kwd )
            elif kwd['action'] == "remove_datasets":
                msg = self.remove_datasets( **kwd )
            elif kwd['action'] == "tool_reload":
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

    def info_delete_userless_histories( self, **kwd ):
        # Provide info about the histories and datasets that will be affected if the 
        # delete_userless_histories function is executed.
        params = util.Params( kwd )
        msg = ''
        if params.days1:
            if params.passwd==self.app.config.admin_pass:
                days = int( params.days1 )
                histories = []
                history_count = 0
                dataset_count = 0
                now  = time.time()
                ht = self.app.model.History.table
                dt = self.app.model.Dataset.table   
                
                for row in ht.select( ( ht.c.user_id==None ) & ( ht.c.deleted=='f' ) ).execute():
                    last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
                    diff = (now-last)/3600/24 # days
                    if diff > days:
                        histories.append( row.id )
                        history_count += 1
                for row in dt.select( dt.c.deleted=='f' ).execute():
                    if row.history_id in histories:
                        dataset_count += 1
                msg = "%d histories ( including a total of %d datasets ) will be deleted." %( history_count, dataset_count )
            else:
                msg = "Invalid password"
        else:
            msg = "Enter the number of days."
        return msg

    def delete_userless_histories( self, **kwd ):
        # Deletes userless histories whose update_time value is older than the specified number of days.
        # A list of each of the affected history records is generated during the process, which is then 
        # used to find all undeleted datasets that are associated with these histories.  Each of these 
        # datasets is then deleted ( by setting the Dataset.deleted column to 't', nothing is removed
        # from the file system ).
        params = util.Params( kwd )
        msg = ''
        if params.days2:
            if params.passwd==self.app.config.admin_pass:
                days = int( params.days2 )
                histories = []
                history_count = 0
                dataset_count = 0
                now = time.time()
                ht = self.app.model.History.table
                dt = self.app.model.Dataset.table    
                
                # Generate a list of histories, deleting userless histories along the way.
                for row in ht.select( ( ht.c.user_id==None ) & ( ht.c.deleted=='f' ) ).execute():
                    last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
                    diff = (now-last)/3600/24 # days
                    if diff > days:
                        history = self.app.model.History.get( row.id )
                        histories.append( row.id )
                        # Delete the history so that it can be purged at some lateer time.
                        history.deleted = True
                        history_count += 1
                # Delete all datasets associated with previously deleted userless histories
                for row in dt.select( dt.c.deleted=='f' ).execute():
                    if row.history_id in histories:
                        data = self.app.model.Dataset.get( row.id )
                        data.deleted = True
                        dataset_count += 1
                try:
                    self.app.model.flush()
                    msg = "Deleted %d histories ( including a total of %d datasets )." % ( history_count, dataset_count )
                except:
                    msg = "Problem flushing app.model when deleting %d histories ( including a total of %d datasets )." % ( history_count, dataset_count )
            else:
                msg = "Invalid password"
        else:
            msg = "Enter the number of days."
        return msg

    def info_purge_histories( self, **kwd ):
        # Provide info about the histories and datasets that will be affected if the 
        # purge_histories function is executed.
        params = util.Params( kwd )
        msg = ''
        if params.days3:
            if params.passwd==self.app.config.admin_pass:
                days = int( params.days3 )
                histories = []
                history_count = 0
                dataset_count = 0
                now  = time.time()
                ht = self.app.model.History.table
                dt = self.app.model.Dataset.table   
                
                for row in ht.select( ( ht.c.deleted=='t' ) & ( ht.c.purged=='f' ) ).execute():
                    last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
                    diff = (now-last)/3600/24 # days
                    if diff > days:
                        histories.append( row.id )
                        history_count += 1
                for row in dt.select( dt.c.purged=='f' ).execute():
                    if row.history_id in histories:
                        dataset_count += 1
                msg = "%d histories ( including a total of %d datasets ) will be purged." %( history_count, dataset_count )
            else:
                msg = "Invalid password"
        else:
            msg = "Enter the number of days."
        return msg

    def purge_histories( self, **kwd ):
        # Purges deleted histories whose update_time value is older than the specified number of days.
        # A list of each of the affected history records is generated during the process, which is then 
        # used to find all non-purged datasets that are associated with these histories.  Each of these 
        # datasets is then purged by doing the following:
        #   1. The string "_purged" is appended to the dataset file name, renaming the file
        #   2. The dataset table record's deleted column is set to 't'
        #   3. The dataset table record's purged column is set to 't'
        #   4. The dataset table record's file_size column is set to 0
        # Nothing is removed from the file system.
        params = util.Params( kwd )
        msg = ''
        if params.days4:
            if params.passwd==self.app.config.admin_pass:
                days = int( params.days4 )
                history_count = 0
                total_datasets_purged = 0
                now  = time.time()
                ht = self.app.model.History.table
                dt = self.app.model.Dataset.table   
                
                for row in ht.select( ( ht.c.deleted=='t' ) & ( ht.c.purged=='f' ) ).execute():
                    last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
                    diff = (now-last)/3600/24 # days
                    if diff > days:
                        dataset_count = 0
                        history = self.app.model.History.get( row.id )
                        # Purge the history, this will also purge all datasets associated with the history.
                        errmsg, dataset_count = history.purge()
                        if errmsg:
                            msg += errmsg + "\n"
                        else:
                            history_count += 1
                        total_datasets_purged += dataset_count
                msg += "%d histories ( including a total of %d datasets ) purged." %( history_count, total_datasets_purged )
            else:
                msg = "Invalid password"
        else:
            msg = "Enter the number of days."
        return msg

    def info_purge_datasets( self, **kwd ):
        # Provide info about the datasets that will be affected if the purge_datasets function is executed.
        params = util.Params( kwd )
        msg = ''
        if params.days5:
            if params.passwd==self.app.config.admin_pass:
                days = int( params.days5 )
                dataset_count = 0
                now = time.time()
                dt = self.app.model.Dataset.table
            
                for row in dt.select( ( dt.c.purged=='f' ) & ( dt.c.deleted=='t' ) ).execute():
                    last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) )
                    diff = (now-last)/3600/24 # days
                    if diff > days:
                        dataset_count += 1
                msg = '%d datasets will be purged.' %dataset_count
            else:
                msg = "Invalid password"
        else:
            msg = "Enter the number of days."
        return msg

    def purge_datasets( self, **kwd ):
        # Purges deleted datasets whose update_time value older than specified number of days by doing
        # the following:
        #   1. The string "_purged" is appended to the dataset file name, renaming the file
        #   2. The dataset table record's deleted column is set to 't'
        #   3. The dataset table record's purged column is set to 't'
        #   4. The dataset table record's file_size column is set to 0
        # TODO: Nothing is currently removed from the file system, but when we are comfortable with the 
        # purge process, the Dataset.purge() function should be modified to delete the file from disk
        # rather than simply renaming it.
        params = util.Params( kwd )
        msg = ''
        if params.days6:
            if params.passwd==self.app.config.admin_pass:
                days = int( params.days6 )
                dataset_count = 0
                now = time.time()
                dt = self.app.model.Dataset.table
            
                for row in dt.select( ( dt.c.purged=='f' ) & ( dt.c.deleted=='t' ) ).execute():
                    last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) )
                    diff = (now-last)/3600/24 # days
                    if diff > days:
                        data = self.app.model.Dataset.get( row.id )
                        errmsg = data.purge()
                        if errmsg:
                            print errmsg
                        else:
                            dataset_count += 1
                msg = 'Purged %d datasets.' % dataset_count
            else:
                msg = "Invalid password"
        else:
            msg = "Enter the number of days."
        return msg

    # TODO: When we are comfortable with the purge process, eliminate these 2 functions below and
    # enhance the purge_datasets function above to display the freed disk space.
    # These functions should not be eliminated until they have been executed, because the first
    # time that the purge_datasets() function is executed, the dataset files on disk are only
    # renamed, so the remove_datasets() function below will need to be used to free up the disk space.

    def info_remove_datasets( self, **kwd ):
        # Provide info about the datasets that will be affected if the remove_datasets function is executed.
        params = util.Params( kwd )
        msg = ''
        if params.days7:
            if params.passwd==self.app.config.admin_pass:
                days = int( params.days7 )
                dataset_count = 0
                total_disk_space = 0
                now = time.time()
                dt = self.app.model.Dataset.table
            
                for row in dt.select( dt.c.purged=='t' ).execute():
                    last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) )
                    diff = (now-last)/3600/24 # days
                    if diff > days:
                        data = self.app.model.Dataset.get( row.id )
                        purged_file_name = data.file_name + "_purged"
                        if os.path.isfile( purged_file_name ):
                            dataset_count += 1
                            try:
                                total_disk_spcae += row.file_size
                            except:
                                pass
                msg = str( dataset_count ) + " datasets will be removed from disk. Total disk space that will be freed up: " + str( total_disk_space )
            else:
                msg = "Invalid password"
        else:
            msg = "Enter the number of days."
        return msg

    def remove_datasets( self, **kwd ):
        # Remove all previously purged dataset files from disk.
        params = util.Params( kwd )
        msg = ''
        if params.days8:
            if params.passwd==self.app.config.admin_pass:
                days = int( params.days8 )
                dataset_count = 0
                total_disk_space = 0
                now = time.time()
                dt = self.app.model.Dataset.table
            
                for row in dt.select( dt.c.purged=='t' ).execute():
                    last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) )
                    diff = (now-last)/3600/24 # days
                    if diff > days:
                        data = self.app.model.Dataset.get( row.id )
                        errmsg = data.remove_from_disk()
                        if errmsg:
                            msg += errmsg + "\n"
                        else:
                            dataset_count += 1
                            try:
                                total_disk_spcae += row.file_size
                            except:
                                pass
                msg += str( dataset_count ) + " datasets removed from disk. Total disk space freed up: " + str( total_disk_space )
            else:
                msg = "Invalid password"
        else:
            msg = "Enter the number of days."
        return msg

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
