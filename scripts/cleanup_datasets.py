#!/usr/bin/env python2.4
#Dan Blankenberg

import sys, os, time, ConfigParser
from optparse import OptionParser
import galaxy.app

def main():
    parser = OptionParser()
    parser.add_option( "-d", "--days", dest="days", action="store", type="int", help="number of days (60)", default=60 )
    parser.add_option( "-1", "--info_delete_userless_histories", action="store_true", dest="info_delete_userless_histories", default=False, help="info about the histories and datasets that will be affected by delete_userless_histories()" )
    parser.add_option( "-2", "--delete_userless_histories", action="store_true", dest="delete_userless_histories", default=False, help="delete userless histories and datasets" )
    parser.add_option( "-3", "--info_purge_histories", action="store_true", dest="info_purge_histories", default=False, help="info about histories and datasets that will be affected by purge_histories()" )
    parser.add_option( "-4", "--purge_histories", action="store_true", dest="purge_histories", default=False, help="purge deleted histories" )
    parser.add_option( "-5", "--info_purge_datasets", action="store_true", dest="info_purge_datasets", default=False, help="info about the datasets that will be affected by purge_datasets()" )
    parser.add_option( "-6", "--purge_datasets", action="store_true", dest="purge_datasets", default=False, help="purge deleted datasets" )
    parser.add_option( "-7", "--info_remove_datasets", action="store_true", dest="info_remove_datasets", default=False, help="infor about the datasets that will be affected by remove_datasets()" )
    parser.add_option( "-8", "--remove_datasets", action="store_true", dest="remove_datasets", default=False, help="remove purged datasets from disk" )
    ( options, args ) = parser.parse_args()
    ini_file = args[0]
    
    if not ( options.info_delete_userless_histories ^ options.delete_userless_histories ^ \
             options.info_purge_histories ^ options.purge_histories ^ \
             options.info_purge_datasets ^ options.purge_datasets ^ \
             options.info_remove_datasets ^ options.remove_datasets ):
        parser.print_help()
        sys.exit(0)
    
    conf_parser = ConfigParser.ConfigParser( {'here':os.getcwd()} )
    conf_parser.read( ini_file )
    configuration = {}
    for key, value in conf_parser.items( "app:main" ):
        configuration[key] = value
    app = galaxy.app.UniverseApplication( global_conf = ini_file, **configuration )
    print "\nHandling stuff older than %i days\n" %options.days
    total_disk_space = 0
    if options.info_delete_userless_histories:
        info_delete_userless_histories( app, options.days )
    elif options.delete_userless_histories:
        delete_userless_histories( app, options.days )
    if options.info_purge_histories:
        info_purge_histories( app, options.days )
    elif options.purge_histories:
        purge_histories( app, options.days )
    elif options.info_purge_datasets:
        info_purge_datasets( app, options.days )
    elif options.purge_datasets:
        purge_datasets( app, options.days )
    elif options.info_remove_datasets:
        info_remove_datasets( app, options.days )
    elif options.remove_datasets:
        remove_datasets( app, options.days )
    print "\n\n"
    app.shutdown()
    sys.exit(0)

def info_delete_userless_histories( app, days ):
    # Provide info about the histories and datasets that will be affected if the 
    # delete_userless_histories function is executed.

    histories = []
    history_count = 0
    dataset_count = 0
    now  = time.time()
    ht = app.model.History.table
    dt = app.model.Dataset.table   
    
    for row in ht.select( ( ht.c.user_id==None ) & ( ht.c.deleted=='f' ) ).execute():
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
        diff = (now-last)/3600/24 # days
        if diff > days:
            histories.append( row.id )
            print "History id %s will be deleted." %str( row.id )
            history_count += 1
    for row in dt.select( dt.c.deleted=='f' ).execute():
        if row.history_id in histories:
            print "Dataset id %s will be deleted." %str( row.id )
            dataset_count += 1
    print "%d histories ( including a total of %d datasets ) will be deleted." %( history_count, dataset_count )

def delete_userless_histories( app, days ):
    # Deletes userless histories whose update_time value is older than the specified number of days.
    # A list of each of the affected history records is generated during the process, which is then 
    # used to find all undeleted datasets that are associated with these histories.  Each of these 
    # datasets is then deleted ( by setting the Dataset.deleted column to 't', nothing is removed
    # from the file system ).

    histories = []
    history_count = 0
    dataset_count = 0
    now = time.time()
    ht = app.model.History.table
    dt = app.model.Dataset.table    
    
    # Generate a list of histories, deleting userless histories along the way.
    for row in ht.select( ( ht.c.user_id==None ) & ( ht.c.deleted=='f' ) ).execute():
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
        diff = (now-last)/3600/24 # days
        if diff > days:
            history = app.model.History.get( row.id )
            histories.append( row.id )
            # Delete the history so that it can be purged at some lateer time.
            history.deleted = True
            print "Updated history table, setting id %s to deleted." %str( row.id )
            history_count += 1
    # Delete all datasets associated with previously deleted userless histories
    for row in dt.select( dt.c.deleted=='f' ).execute():
        if row.history_id in histories:
            data = app.model.Dataset.get( row.id )
            data.deleted = True
            print "Updated dataset table, setting id %s to deleted." %str( row.id )
            dataset_count += 1
    try:
        app.model.flush()
        print "Deleted %d histories ( including a total of %d datasets )." % ( history_count, dataset_count )
    except:
        print "Problem flushing app.model when deleting %d histories ( including a total of %d datasets )." % ( history_count, dataset_count )

def info_purge_histories( app, days ):
    # Provide info about the histories and datasets that will be affected if the 
    # purge_histories function is executed.

    histories = []
    history_count = 0
    dataset_count = 0
    now  = time.time()
    ht = app.model.History.table
    dt = app.model.Dataset.table   
    
    for row in ht.select( ( ht.c.deleted=='t' ) & ( ht.c.purged=='f' ) ).execute():
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
        diff = (now-last)/3600/24 # days
        if diff > days:
            histories.append( row.id )
            print "History id %s will be purged." %str( row.id )
            history_count += 1
    for row in dt.select( dt.c.purged=='f' ).execute():
        if row.history_id in histories:
            print "Dataset id %s will be purged." %str( row.id )
            dataset_count += 1
    print "%d histories ( including a total of %d datasets ) will be purged." %( history_count, dataset_count )

def purge_histories( app, days ):
    # Purges deleted histories whose update_time value is older than the specified number of days.
    # A list of each of the affected history records is generated during the process, which is then 
    # used to find all non-purged datasets that are associated with these histories.  Each of these 
    # datasets is then purged by doing the following:
    #   1. The string "_purged" is appended to the dataset file name, renaming the file
    #   2. The dataset table record's deleted column is set to 't'
    #   3. The dataset table record's purged column is set to 't'
    #   4. The dataset table record's file_size column is set to 0
    # Nothing is removed from the file system.

    history_count = 0
    total_datasets_purged = 0
    now  = time.time()
    ht = app.model.History.table
    dt = app.model.Dataset.table   
    
    for row in ht.select( ( ht.c.deleted=='t' ) & ( ht.c.purged=='f' ) ).execute():
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
        diff = (now-last)/3600/24 # days
        if diff > days:
            dataset_count = 0
            history = app.model.History.get( row.id )
            # Purge the history, this will also purge all datasets associated with the history.
            errmsg, dataset_count = history.purge()
            if errmsg:
                print errmsg
            else:
                print "History id %s ( including a total of %d datasets ) purged." %( str( row.id ), dataset_count )
                history_count += 1
            total_datasets_purged += dataset_count
    print "%d histories ( including a total of %d datasets ) purged." %( history_count, total_datasets_purged )

def info_purge_datasets( app, days ):
    # Provide info about the datasets that will be affected if the purge_datasets function is executed.
    dataset_count = 0
    now = time.time()
    dt = app.model.Dataset.table

    for row in dt.select( ( dt.c.purged=='f' ) & ( dt.c.deleted=='t' ) ).execute():
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) )
        diff = (now-last)/3600/24 # days
        if diff > days:
            print "Dataset id %s will be purged." %str( row.id )
            dataset_count += 1
    print '%d datasets will be purged.' %dataset_count

def purge_datasets( app, days ):
    # Purges deleted datasets whose update_time value older than specified number of days by doing
    # the following:
    #   1. The string "_purged" is appended to the dataset file name, renaming the file
    #   2. The dataset table record's deleted column is set to 't'
    #   3. The dataset table record's purged column is set to 't'
    #   4. The dataset table record's file_size column is set to 0
    # TODO: Nothing is currently removed from the file system, but when we are comfortable with the 
    # purge process, the Dataset.purge() function should be modified to delete the file from disk
    # rather than simply renaming it.

    dataset_count = 0
    now = time.time()
    dt = app.model.Dataset.table

    for row in dt.select( ( dt.c.purged=='f' ) & ( dt.c.deleted=='t' ) ).execute():
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) )
        diff = (now-last)/3600/24 # days
        if diff > days:
            data = app.model.Dataset.get( row.id )
            errmsg = data.purge()
            if errmsg:
                print errmsg
            else:
                print "Purged dataset id %s." %str( row.id )
                dataset_count += 1
    print 'Purged %d datasets.' % dataset_count


# TODO: When we are comfortable with the purge process, eliminate these 2 functions below and
# enhance the purge_datasets function above to display the freed disk space.
# These functions should not be eliminated until they have been executed, because the first
# time that the purge_datasets() function is executed, the dataset files on disk are only
# renamed, so the remove_datasets() function below will need to be used to free up the disk space.

def info_remove_datasets( app, days ):
    # Provide info about the datasets that will be affected if the remove_datasets function is executed.
    dataset_count = 0
    total_disk_space = 0
    now = time.time()
    dt = app.model.Dataset.table

    for row in dt.select( dt.c.purged=='t' ).execute():
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) )
        diff = (now-last)/3600/24 # days
        if diff > days:
            data = app.model.Dataset.get( row.id )
            # First try filename directly under file_path
            purged_file_name = os.path.join( data.file_path, "dataset_%d.dat_purged" % data.id )
            # Only use that filename if it already exists (backward compatibility),
            # otherwise construct hashed path
            if not os.path.exists( purged_file_name ):
                dir = os.path.join( data.file_path, *directory_hash_id( data.id ) )
                # Look for file inside hashed directory
                purged_file_name = os.path.abspath( os.path.join( dir, "dataset_%d.dat_purged" % data.id ) )
            if os.path.isfile( purged_file_name ):
                print "Dataset id %s with file_size %s will be removed from disk." %( str( row.id ), str( row.file_size ) )
                dataset_count += 1
                try:
                    total_disk_spcae += row.file_size
                except:
                    pass
    print '%d datasets will be removed from disk.' %dataset_count
    print "Total disk space that will be freed up: ", total_disk_space

def remove_datasets( app, days ):
    # Remove all previously purged dataset files from disk.
    dataset_count = 0
    total_disk_space = 0
    now = time.time()
    dt = app.model.Dataset.table

    for row in dt.select( dt.c.purged=='t' ).execute():
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) )
        diff = (now-last)/3600/24 # days
        if diff > days:
            data = app.model.Dataset.get( row.id )
            errmsg = data.remove_from_disk()
            if errmsg:
                print errmsg
            else:
                print "Removed dataset id %s with file_size %s." %( str( row.id ), str( row.file_size ) )
                dataset_count += 1
                try:
                    total_disk_spcae += row.file_size
                except:
                    pass
    print '%d datasets removed from disk.' %dataset_count
    print "Total disk space freed up: ", total_disk_space

if __name__ == "__main__":
    main()