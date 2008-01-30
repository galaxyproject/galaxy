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
    ( options, args ) = parser.parse_args()
    ini_file = args[0]
    
    if not ( options.info_delete_userless_histories ^ options.delete_userless_histories ^ \
             options.info_purge_histories ^ options.purge_histories ^ \
             options.info_purge_datasets ^ options.purge_datasets ):
        parser.print_help()
        sys.exit(0)
    
    conf_parser = ConfigParser.ConfigParser( {'here':os.getcwd()} )
    conf_parser.read( ini_file )
    configuration = {}
    for key, value in conf_parser.items( "app:main" ):
        configuration[key] = value
    app = galaxy.app.UniverseApplication( global_conf = ini_file, **configuration )
    print "\n# Handling stuff older than %i days\n" %options.days
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
    
    print '# The following userless histories will be deleted'
    for row in ht.select( ( ht.c.user_id==None ) & ( ht.c.deleted=='f' ) ).execute():
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
        diff = (now-last)/3600/24 # days
        if diff > days:
            histories.append( row.id )
            print '%s' %str( row.id )
            history_count += 1
    print '# The following associated datasets will be deleted'
    for row in dt.select( dt.c.deleted=='f' ).execute():
        if row.history_id in histories:
            print "%s" %str( row.id )
            dataset_count += 1
    print "# %d histories ( including a total of %d datasets ) will be deleted\n" %( history_count, dataset_count )

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
    
    print '# The following userless histories are now deleted'
    for row in ht.select( ( ht.c.user_id==None ) & ( ht.c.deleted=='f' ) ).execute():
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
        diff = (now-last)/3600/24 # days
        if diff > days:
            history = app.model.History.get( row.id )
            histories.append( row.id )
            history.deleted = True
            print '%s' %str( row.id )
            history_count += 1
    # Delete all datasets associated with previously deleted userless histories
    print '# The following associated datasets are now deleted'
    for row in dt.select( dt.c.deleted=='f' ).execute():
        if row.history_id in histories:
            data = app.model.Dataset.get( row.id )
            data.deleted = True
            print '%s' %str( row.id )
            dataset_count += 1
    try:
        app.model.flush()
        print "# Deleted %d histories ( including a total of %d datasets )\n" % ( history_count, dataset_count )
    except Exception, exc:
        print "# Error: exception, %s caught attempting to flush app.model when deleting %d histories ( including a total of %d datasets )\n" % ( str( exc ), history_count, dataset_count )

def info_purge_histories( app, days ):
    # Provide info about the histories and datasets that will be affected if the 
    # purge_histories function is executed.
    histories = []
    history_count = 0
    dataset_count = 0
    now  = time.time()
    ht = app.model.History.table
    dt = app.model.Dataset.table   

    print '# The following deleted histories will be purged'
    for row in ht.select( ( ht.c.deleted=='t' ) & ( ht.c.purged=='f' ) ).execute():
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
        diff = (now-last)/3600/24 # days
        if diff > days:
            histories.append( row.id )
            print '%s' %str( row.id )
            history_count += 1
    print '# The following associated datasets will be purged'
    for row in dt.select( dt.c.purged=='f' ).execute():
        if row.history_id in histories:
            data = app.model.Dataset.get( row.id )
            print "%s" %str( data.file_name )
            dataset_count += 1
    print '# %d histories ( including a total of %d datasets ) will be purged\n' %( history_count, dataset_count )

def purge_histories( app, days ):
    # Purges deleted histories whose update_time is older than the specified number of days.
    # A list of each of the affected history records is generated during the process, which is then 
    # used to find all non-purged datasets that are associated with these histories.  Each of these 
    # datasets is then purged.
    history_count = 0
    total_datasets_purged = 0
    now  = time.time()
    ht = app.model.History.table
    dt = app.model.Dataset.table   

    print '# The following deleted histories are now purged'
    for row in ht.select( ( ht.c.deleted=='t' ) & ( ht.c.purged=='f' ) ).execute():
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) ) 
        diff = (now-last)/3600/24 # days
        if diff > days:
            history = app.model.History.get( row.id )
            # Purge the history, this will also purge all datasets associated with the history.
            errmsg, datasets = history.purge()
            if errmsg:
                print errmsg
            else:
                print '%s' %str( row.id )
                print '# Associated  datasets:'
                for file_name in datasets:
                    print "%s" %file_name
                history_count += 1
            total_datasets_purged += len( datasets )
    print '# %d histories ( including a total of %d datasets ) purged\n' %( history_count, total_datasets_purged )

def info_purge_datasets( app, days ):
    # Provide info about the datasets that will be affected if the purge_datasets function is executed.
    dataset_count = 0
    total_disk_space = 0
    now = time.time()
    dt = app.model.Dataset.table

    print '# The following deleted datasets will be purged'
    for row in dt.select( ( dt.c.deleted=='t' ) & ( dt.c.purged=='f' ) ).execute():
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) )
        diff = (now-last)/3600/24 # days
        if diff > days:
            data = app.model.Dataset.get( row.id )
            print '%s' %str( data.file_name )
            dataset_count += 1
            try:
                total_disk_space += row.file_size
            except:
                pass
    print '# %d datasets will be purged' %dataset_count
    print '# Total disk space that will be freed up: ', total_disk_space, '\n'

def purge_datasets( app, days ):
    # Purges deleted datasets whose update_time value older than specified number of days.
    dataset_count = 0
    total_disk_space = 0
    now = time.time()
    dt = app.model.Dataset.table

    print '# The following deleted datasets are now purged'
    for row in dt.select( ( dt.c.deleted=='t' ) & ( dt.c.purged=='f' ) ).execute():
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) )
        diff = (now-last)/3600/24 # days
        if diff > days:
            data = app.model.Dataset.get( row.id )
            errmsg = data.purge()
            if errmsg:
                print errmsg
            else:
                print '%s' %str( data.file_name )
                dataset_count += 1
                try:
                    total_disk_space += row.file_size
                except:
                    pass
    print '# %d datasets purged' % dataset_count
    print '# Total disk space freed up: ', total_disk_space, '\n'

if __name__ == "__main__":
    main()