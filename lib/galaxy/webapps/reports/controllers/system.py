import operator, os
from datetime import datetime, timedelta
from galaxy.web.base.controller import *
from galaxy import model
from galaxy.model.orm import *
import logging
log = logging.getLogger( __name__ )

class System( BaseUIController ):
    @web.expose
    def index( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
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
                userless_histories_days, message = self.userless_histories( trans, **kwd )
            elif kwd['action'] == "deleted_histories":
                deleted_histories_days, message = self.deleted_histories( trans, **kwd )
            elif kwd['action'] == "deleted_datasets":
                deleted_datasets_days, message = self.deleted_datasets( trans, **kwd )
        return trans.fill_template( '/webapps/reports/system.mako',
                                    file_path=file_path,
                                    disk_usage=disk_usage,
                                    datasets=datasets,
                                    file_size_str=file_size_str,
                                    userless_histories_days=userless_histories_days,
                                    deleted_histories_days=deleted_histories_days,
                                    deleted_datasets_days=deleted_datasets_days,
                                    message=message )
    def userless_histories( self, trans, **kwd ):
        """The number of userless histories and associated datasets that have not been updated for the specified number of days."""
        params = util.Params( kwd )
        message = ''
        if params.userless_histories_days:
            userless_histories_days = int( params.userless_histories_days )
            cutoff_time = datetime.utcnow() - timedelta( days=userless_histories_days )
            history_count = 0
            dataset_count = 0
            for history in trans.sa_session.query( model.History ) \
                                           .filter( and_( model.History.table.c.user_id == None,
                                                          model.History.table.c.deleted == True,
                                                          model.History.table.c.update_time < cutoff_time ) ):
                for dataset in history.datasets:
                    if not dataset.deleted:
                        dataset_count += 1
                history_count += 1
            message = "%d userless histories ( including a total of %d datasets ) have not been updated for at least %d days." %( history_count, dataset_count, userless_histories_days )
        else:
            message = "Enter the number of days."
        return str( userless_histories_days ), message
    def deleted_histories( self, trans, **kwd ):
        """
        The number of histories that were deleted more than the specified number of days ago, but have not yet been purged.
        Also included is the number of datasets associated with the histories.
        """
        params = util.Params( kwd )
        message = ''
        if params.deleted_histories_days:
            deleted_histories_days = int( params.deleted_histories_days )
            cutoff_time = datetime.utcnow() - timedelta( days=deleted_histories_days )
            history_count = 0
            dataset_count = 0
            disk_space = 0
            histories = trans.sa_session.query( model.History ) \
                                        .filter( and_( model.History.table.c.deleted == True,
                                                       model.History.table.c.purged == False,
                                                       model.History.table.c.update_time < cutoff_time ) ) \
                                        .options( eagerload( 'datasets' ) )

            for history in histories:
                for hda in history.datasets:
                    if not hda.dataset.purged:
                        dataset_count += 1
                        try:
                            disk_space += hda.dataset.file_size
                        except:
                            pass
                history_count += 1
            message = "%d histories ( including a total of %d datasets ) were deleted more than %d days ago, but have not yet been purged.  Disk space: " %( history_count, dataset_count, deleted_histories_days ) + str( disk_space )
        else:
            message = "Enter the number of days."
        return str( deleted_histories_days ), message
    def deleted_datasets( self, trans, **kwd ):
        """The number of datasets that were deleted more than the specified number of days ago, but have not yet been purged."""
        params = util.Params( kwd )
        message = ''
        if params.deleted_datasets_days:
            deleted_datasets_days = int( params.deleted_datasets_days )
            cutoff_time = datetime.utcnow() - timedelta( days=deleted_datasets_days )
            dataset_count = 0
            disk_space = 0
            for dataset in trans.sa_session.query( model.Dataset ) \
                                           .filter( and_( model.Dataset.table.c.deleted == True,
                                                          model.Dataset.table.c.purged == False,
                                                          model.Dataset.table.c.update_time < cutoff_time ) ):
                dataset_count += 1
                try:
                    disk_space += dataset.file_size
                except:
                    pass
            message = str( dataset_count ) + " datasets were deleted more than " + str( deleted_datasets_days ) + \
            " days ago, but have not yet been purged, disk space: " + nice_size( disk_space ) + "."
        else:
            message = "Enter the number of days."
        return str( deleted_datasets_days ), message
    @web.expose
    def dataset_info( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        dataset = trans.sa_session.query( model.Dataset ).get( trans.security.decode_id( kwd.get( 'id', '' ) ) )
        # Get all associated hdas and lddas that use the same disk file.
        associated_hdas = trans.sa_session.query( trans.model.HistoryDatasetAssociation ) \
                                          .filter( and_( trans.model.HistoryDatasetAssociation.deleted == False,
                                                         trans.model.HistoryDatasetAssociation.dataset_id == dataset.id ) ) \
                                          .all()
        associated_lddas = trans.sa_session.query( trans.model.LibraryDatasetDatasetAssociation ) \
                                           .filter( and_( trans.model.LibraryDatasetDatasetAssociation.deleted == False,
                                                          trans.model.LibraryDatasetDatasetAssociation.dataset_id == dataset.id ) ) \
                                           .all()
        return trans.fill_template( '/webapps/reports/dataset_info.mako',
                                    dataset=dataset,
                                    associated_hdas=associated_hdas,
                                    associated_lddas=associated_lddas,
                                    message=message )
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
        datasets = trans.sa_session.query( model.Dataset ) \
                                   .filter( and_( model.Dataset.table.c.purged == False,
                                                  model.Dataset.table.c.file_size > min_file_size ) ) \
                                   .order_by( desc( model.Dataset.table.c.file_size ) )
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
