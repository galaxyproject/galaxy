import operator, os
from datetime import datetime, timedelta
from galaxy.webapps.reports.base.controller import *
import pkg_resources
pkg_resources.require( "sqlalchemy>=0.3" )
from sqlalchemy import eagerload, desc
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
        return trans.fill_template( 'system.mako', file_path=file_path, disk_usage=disk_usage, datasets=datasets, file_size_str=file_size_str, userless_histories_days=userless_histories_days, deleted_histories_days=deleted_histories_days, deleted_datasets_days=deleted_datasets_days, msg=msg )

    def userless_histories( self, **kwd ):
        """The number of userless histories and associated datasets that have not been updated for the specified number of days."""
        params = util.Params( kwd )
        msg = ''
        if params.userless_histories_days:
            userless_histories_days = int( params.userless_histories_days )
            cutoff_time = datetime.utcnow() - timedelta( days=userless_histories_days )
            history_count = 0
            dataset_count = 0
            h = self.app.model.History
            where = ( h.table.c.user_id==None ) & ( h.table.c.deleted=='f' ) & ( h.table.c.update_time < cutoff_time )
            histories = h.query().filter( where ).options( eagerload( 'datasets' ) )
    
            for history in histories:
                for dataset in history.datasets:
                    if not dataset.deleted:
                        dataset_count += 1
                history_count += 1
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
            cutoff_time = datetime.utcnow() - timedelta( days=deleted_histories_days )
            history_count = 0
            dataset_count = 0
            disk_space = 0
            h = self.app.model.History
            d = self.app.model.Dataset
            where = ( h.table.c.deleted=='t' ) & ( h.table.c.purged=='f' ) & ( h.table.c.update_time < cutoff_time )
            
            histories = h.query().filter( where ).options( eagerload( 'datasets' ) )   
            for history in histories:
                for dataset in history.datasets:
                    if not dataset.purged:
                        dataset_count += 1
                        try:
                            disk_space += dataset.file_size
                        except:
                            pass
                history_count += 1
            msg = "%d histories ( including a total of %d datasets ) were deleted more than %d days ago, but have not yet been purged.  Disk space: " %( history_count, dataset_count, deleted_histories_days ) + str( disk_space )
        else:
            msg = "Enter the number of days."
        return str( deleted_histories_days ), msg

    def deleted_datasets( self, **kwd ):
        """The number of datasets that were deleted more than the specified number of days ago, but have not yet been purged."""
        params = util.Params( kwd )
        msg = ''
        if params.deleted_datasets_days:
            deleted_datasets_days = int( params.deleted_datasets_days )
            cutoff_time = datetime.utcnow() - timedelta( days=deleted_datasets_days )
            dataset_count = 0
            disk_space = 0
            d = self.app.model.Dataset
            where = ( d.table.c.deleted=='t' ) & ( d.table.c.purged=='f' ) & ( d.table.c.update_time < cutoff_time )
    
            datasets = d.query().filter( where )
            for dataset in datasets:
                dataset_count += 1
                try:
                    disk_space += dataset.file_size
                except:
                    pass
            msg = str( dataset_count ) + " datasets were deleted more than " + str( deleted_datasets_days ) + \
            " days ago, but have not yet been purged, disk space: " + str( disk_space ) + "."
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
        min_file_size = 2**32 # 4 Gb
        file_size_str = nice_size( min_file_size )
        hda = trans.model.HistoryDatasetAssociation
        d = trans.model.Dataset
        datasets = []
        where = ( d.table.c.file_size > min_file_size )
        dataset_rows = d.query().filter( where ).order_by( desc( d.table.c.file_size ) )

        for dataset in dataset_rows:
            history_dataset_assoc = hda.filter_by( dataset_id=dataset.id ).order_by( desc( hda.table.c.history_id ) ).all()[0]
            datasets.append( ( dataset.id, str( dataset.update_time )[0:10], history_dataset_assoc.history_id, dataset.deleted, dataset.file_size ) )
        return file_path, disk_usage, datasets, file_size_str

def nice_size( size ):
    """Returns a readably formatted string with the size"""
    words = [ 'bytes', 'Kb', 'Mb', 'Gb' ]
    try:
        size = float( size )
    except:
        return '??? bytes'
    for ind, word in enumerate( words ):
        step  = 1024 ** ( ind + 1 )
        if step > size:
            size = size / float( 1024 ** ind )
            out  = "%.1f %s" % ( size, word )
            return out
    return '??? bytes'

