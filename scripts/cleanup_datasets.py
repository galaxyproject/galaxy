#!/usr/bin/env python2.4
#Dan Blankenberg

import sys, os, time, ConfigParser
from optparse import OptionParser
import galaxy.app

def main():
    parser = OptionParser()
    parser.add_option( "-d", "--days", dest="days", action="store", type="int", help="number of days (30)", default=30 )
    parser.add_option( "-a", "--abandon", action="store_true", dest="abandon", default=False, help="abandon old, unowned (userless) histories" )
    parser.add_option( "-b", "--info_abandon", action="store_true", dest="info_abandon", default=False, help="info about the histories and datasets that will be affected" )
    parser.add_option( "-p", "--purge", action="store_true", dest="purge", default=False, help="purge old deleted datasets" )
    parser.add_option( "-q", "--info_purge", action="store_true", dest="info_purge", default=False, help="info about the datasets that will be affected" )
    ( options, args ) = parser.parse_args()
    ini_file = args[0]
    
    if not ( options.info_abandon ^ options.info_purge ^ options.purge ^ options.abandon ):
        parser.print_help()
        sys.exit(0)
    
    conf_parser = ConfigParser.ConfigParser( {'here':os.getcwd()} )
    conf_parser.read( ini_file )
    configuration = {}
    for key, value in conf_parser.items("app:main"):
        configuration[key] = value
    app = galaxy.app.UniverseApplication( global_conf = ini_file, **configuration )
    msg = ''
    total_disk_space = 0
    if options.purge:
        msg, total_disk_space = purge( app, options.days )
    elif options.info_purge:
        msg, total_disk_space = info_purge( app, options.days )
    elif options.abandon:
        msg, total_disk_space = abandon( app, options.days )
    elif options.info_abandon:
        msg, total_disk_space = info_abandon( app, options.days )
    app.shutdown()
    if msg:
        print "\nFor stuff older than %i days, %s\n" % ( options.days, msg )
    if total_disk_space >= 0:
        if options.purge:
            print "Total disk space freed up: ", total_disk_space
        else:
            print "Total minimum disk space that will be freed up if datasets are purged: ", total_disk_space
    sys.exit(0)

def abandon( app, days ):
    """
    'Abandons' userless histories whose update_time value is older than the specified number of days 
    by setting the 'deleted' column to 't' in the History table for each History.id whose History.user_id 
    column is null.  A list of each of the affected history records is generated during the process.  
    This list is then used to find all undeleted datasets that are associated with these histories.  Each of
    these datasets is then deleted by setting the Dataset.deleted column to 't'.  Nothing is removed
    from the file system.  This function should be executed in preparation for purging datasets using 
    the purge() function below.
    """
    histories_no_users = []
    history_count = 0
    ht = app.model.History.table

    # Generate a list of userless histories, deleting the histories along the way
    for row in ht.select( ht.c.user_id==None ).execute():
        now  = time.time()
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
        diff = (now-last)/3600/24 # days
        if diff > days:
            histories_no_users.append( row.id )
            if not row.deleted:
                print "Updating history table, setting id %s to deleted." %str( row.id )
                history = app.model.History.get( row.id )
                history.deleted = True
                history_count += 1
    dataset_count = 0
    total_disk_space = 0
    dt = app.model.Dataset.table
    # Delete all datasets associated with previously deleted userless histories
    for row in dt.select( dt.c.deleted=='f' ).execute():
        if row.history_id in histories_no_users:
            print "Updating dataset table, setting id %s to deleted." %str( row.id )
            data = app.model.Dataset.get( row.id )
            data.deleted = True
            dataset_count += 1
            total_disk_space += row.file_size
    try:
        app.model.flush()
    except:
        pass
    msg = 'Deleted %d histories ( including a total of %d datasets ).' % ( history_count, dataset_count )
    return msg, total_disk_space

def info_abandon( app, days ):
    # Provide info about the histories and datasets that will be affected if the abandon function is executed.
    histories_no_users = []
    history_count = 0
    ht = app.model.History.table
    
    for row in ht.select( ht.c.user_id==None ).execute():
        now  = time.time()
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
        diff = (now-last)/3600/24 # days
        if diff > days:
            histories_no_users.append( row.id )
            if not row.deleted:
                print "History id %s will be deleted." %str( row.id )
                history_count += 1
    dataset_count = 0
    total_disk_space = 0
    dt = app.model.Dataset.table
    for row in dt.select( dt.c.deleted=='f' ).execute():
        if row.history_id in histories_no_users:
            print "Dataset id %s with file size %s will be deleted." %( str( row.id ), str( row.file_size ) )
            dataset_count += 1
            total_disk_space += row.file_size
    msg = '%d histories ( including a total of %d datasets ) will be deleted.' % ( history_count, dataset_count )
    return msg, total_disk_space

def purge( app, days ):
    """
    Purges deleted datasets whose create_time column is older than specified number of days by executing 
    the Dataset.purge() function.  This will update the Dataset table, setting Dataset.deleted to 't', 
    Dataset.purged to 't', and Dataset.file_size to 0.  The dataset file will then be removed from the file 
    system.  The create_time column is used because the abandon function, if executed, would have reset the
    update_time column value.
    """
    count = 0
    total_disk_space = 0
    now = time.time()
    dt = app.model.Dataset.table
    for row in dt.select( ( dt.c.purged=='f' ) & ( dt.c.deleted=='t' ) ).execute():
        last = time.mktime( time.strptime( row.create_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) )
        diff = (now-last)/3600/24 # days
        if diff > days:
            print "Purging dataset id %s with file size %s." % ( str( row.id ), str( row.file_size ) )
            data = app.model.Dataset.get( row.id )
            data.purge()
            data.flush()
            count += 1
            total_disk_space += row.file_size
    try:
        app.model.flush()
    except:
        pass
    msg = 'Purged %d datasets.' % count
    return msg, total_disk_space

def info_purge( app, days ):
    # Provide info about the datasets that will be affected if the purge function is executed.
    count = 0
    total_disk_space = 0
    now = time.time()
    dt = app.model.Dataset.table
    for row in dt.select( ( dt.c.purged=='f' ) & ( dt.c.deleted=='t' ) ).execute():
        last = time.mktime( time.strptime( row.create_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) )
        diff = (now-last)/3600/24 # days
        if diff > days:
            print "Dataset id %s with file size %s will be purged." % ( str( row.id ), str( row.file_size ) )
            count += 1
            total_disk_space += row.file_size
    msg = '%d datasets will be purged.' %count
    return msg, total_disk_space

if __name__ == "__main__":
    main()