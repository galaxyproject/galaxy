
import operator, os
from galaxy.webapps.reports.base.controller import *

import logging
log = logging.getLogger( __name__ )

class System( BaseController ):
    @web.expose
    def index( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        
        if params.userless_histories_days:
            userless_histories_days = params.userless_histories_days
        else:
            userless_histories_days = '60'
            
        if params.deleted_histories_days:
            deleted_histories_days = params.deleted_histories_days
        else:
            deleted_histories_days = '60'
            
        if params.deleted_datasets_days:
            deleted_datasets_days = params.deleted_datasets_days
        else:
            deleted_datasets_days = '60'
            
        file_path, disk_usage, datasets, file_size_str = self.disk_usage( trans, **kwd )
        if 'action' in kwd:
            if kwd['action'] == "userless_histories":
                userless_histories_days, msg = self.userless_histories( **kwd )
            elif kwd['action'] == "deleted_histories":
                deleted_histories_days, msg = self.deleted_histories( **kwd )
            elif kwd['action'] == "deleted_datasets":
                deleted_datasets_days, msg = self.deleted_datasets( **kwd )
        return trans.fill_template('system.tmpl', file_path=file_path, disk_usage=disk_usage, datasets=datasets, file_size_str=file_size_str, userless_histories_days=userless_histories_days, deleted_histories_days=deleted_histories_days, deleted_datasets_days=deleted_datasets_days, msg=msg )

    def userless_histories( self, **kwd ):
        """The number of userless histories and associated datasets that have not been updated for the specified number of days."""
        params = util.Params( kwd )
        msg = ''
        if params.userless_histories_days:
            userless_histories_days = int( params.userless_histories_days )
            histories = []
            history_count = 0
            dataset_count = 0
            now  = time.time()
            ht = self.app.model.History.table
            dt = self.app.model.Dataset.table   
            
            for row in ht.select( ( ht.c.user_id==None ) & ( ht.c.deleted=='f' ) ).execute():
                last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
                diff = (now-last)/3600/24 # days
                if diff > userless_histories_days:
                    histories.append( row.id )
                    history_count += 1
            for row in dt.select( dt.c.deleted=='f' ).execute():
                if row.history_id in histories:
                    dataset_count += 1
            msg = "%d userless histories ( including a total of %d datasets ) have not been updated for at least %d days." %( history_count, dataset_count, userless_histories_days )
        else:
            msg = "Enter the number of days."
        return str( userless_histories_days ), msg

    def deleted_histories( self, **kwd ):
        """
        The number of histories that were deleted more than the specified number of days ago, but have not yet been purged.
        Also included is the number of datasets associated with the histories.
        """
        params = util.Params( kwd )
        msg = ''
        if params.deleted_histories_days:
            deleted_histories_days = int( params.deleted_histories_days )
            histories = []
            history_count = 0
            dataset_count = 0
            now  = time.time()
            ht = self.app.model.History.table
            dt = self.app.model.Dataset.table   
            
            for row in ht.select( ( ht.c.deleted=='t' ) & ( ht.c.purged=='f' ) ).execute():
                last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
                diff = (now-last)/3600/24 # days
                if diff > deleted_histories_days:
                    histories.append( row.id )
                    history_count += 1
            for row in dt.select( dt.c.purged=='f' ).execute():
                if row.history_id in histories:
                    dataset_count += 1
            msg = "%d histories ( including a total of %d datasets ) were deleted more than %d days ago, but have not yet been purged." %( history_count, dataset_count, deleted_histories_days )
        else:
            msg = "Enter the number of days."
        return str( deleted_histories_days ), msg

    def deleted_datasets( self, **kwd ):
        """The number of datasets that were deleted more than the specified number of days ago, but have not yet been purged."""
        params = util.Params( kwd )
        msg = ''
        if params.deleted_datasets_days:
            deleted_datasets_days = int( params.deleted_datasets_days )
            dataset_count = 0
            total_disk_space = 0
            now = time.time()
            dt = self.app.model.Dataset.table
        
            for row in dt.select( ( dt.c.deleted=='t' ) & ( dt.c.purged=='f' ) ).execute():
                last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) )
                diff = (now-last)/3600/24 # days
                if diff > deleted_datasets_days:                        
                    data = self.app.model.Dataset.get( row.id )
                    if os.path.exists( data.file_name ):
                        dataset_count += 1
                        try:
                            total_disk_space += row.file_size
                        except:
                            pass
            msg = str( dataset_count ) + " datasets were deleted more than " + str( deleted_datasets_days ) + \
            " days ago, but have not yet been purged, total disk space: " + str( total_disk_space ) + "."
        else:
            msg = "Enter the number of days."
        return str( deleted_datasets_days ), msg

    def get_disk_usage( self, file_path ):
        df_cmd = 'df -h ' + file_path
        is_sym_link = os.path.islink( file_path )
        file_system = disk_size = disk_used = disk_avail = disk_cap_pct = mount = None
        df_file = os.popen( df_cmd )

        while True:
            df_line = df_file.readline()
            df_line = df_line.strip()
            if df_line:
                df_line = df_line.lower()
                if 'filesystem' in df_line or 'proc' in df_line:
                    continue
                elif is_sym_link:
                    if ':' in df_line and '/' in df_line:
                        mount = df_line
                    else:
                        try:
                            disk_size, disk_used, disk_avail, disk_cap_pct, file_system = df_line.split()
                            break
                        except:
                            pass
                else:
                    try:
                        file_system, disk_size, disk_used, disk_avail, disk_cap_pct, mount = df_line.split()
                        break
                    except:
                        pass
            else:
                break # EOF
        df_file.close()
        return ( file_system, disk_size, disk_used, disk_avail, disk_cap_pct, mount  )

    @web.expose
    def disk_usage( self, trans, **kwd ):
        file_path = trans.app.config.file_path
        disk_usage = self.get_disk_usage( file_path )
        min_file_size = 2**30 # 100 MB
        file_size_str = '100 MB'
        datasets = []
        dt = trans.model.Dataset.table

        for row in dt.select( dt.c.file_size>min_file_size ).execute():
            datasets.append( ( row.id, str( row.update_time )[0:10], row.history_id, row.deleted, row.file_size ) )
        datasets = sorted( datasets, key=operator.itemgetter(4), reverse=True )
        return file_path, disk_usage, datasets, file_size_str

