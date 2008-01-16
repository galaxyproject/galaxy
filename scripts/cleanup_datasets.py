#!/usr/bin/env python2.4
#Dan Blankenberg

import sys, os, time, ConfigParser
from optparse import OptionParser
import galaxy.app

def main():
    parser = OptionParser()
    parser.add_option( "-d", "--days", dest="days", action="store", type="int", help="number of days (30)", default=30 )
    parser.add_option( "-a", "--abandon", action="store_true", dest="abandon", default=False, help="abandon old, unowned (userless) histories" )
    parser.add_option( "-p", "--purge", action="store_true", dest="purge", default=False, help="purge old deleted datasets" )
    ( options, args ) = parser.parse_args()
    ini_file = args[0]
    
    if not ( options.purge ^ options.abandon ):
        parser.print_help()
        sys.exit(0)
    
    conf_parser = ConfigParser.ConfigParser( {'here':os.getcwd()} )
    conf_parser.read( ini_file )
    configuration = {}
    for key, value in conf_parser.items("app:main"):
        configuration[key] = value
    app = galaxy.app.UniverseApplication( global_conf = ini_file, **configuration )
    msg = ''
    if options.purge:
        msg = purge( app, options.days )
    elif options.abandon:
        msg = abandon( app, options.days )
    app.shutdown()
    if msg:
        print "\n%s older than %i days.\n" % ( msg, options.days )
    sys.exit(0)

def abandon( app, days ):
    """
    'Abandons' userless histories older than the specified number of days by setting the 'deleted'
    column to 't' in the History table for each History.id whose History.user_id column is null.
    A list of each of the affected history records is generated during the process.  This list is
    then used to find all undeleted datasets that are associated with these histories.  Each of
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
                print "Updating history table, setting id %s to deleted" %str( row.id )
                history = app.model.History.get( row.id )
                history.deleted = True
                history_count += 1
    dataset_count = 0
    dt = app.model.Dataset.table
    # Delete all datasets associated with previously deleted userless histories
    for row in dt.select( dt.c.deleted=='f' ).execute():
        if row.history_id in histories_no_users:
            print "Updating dataset table, setting id %s to deleted" %str( row.id )
            data = app.model.Dataset.get( row.id )
            data.deleted = True
            dataset_count += 1
    try:
        app.model.flush()
    except:
        pass
    msg = 'Deleted %d histories (including a total of %d datasets )' % ( history_count, dataset_count )
    return msg

def purge( app, days ):
    """
    Purges deleted datasets older than specified number of days by executing the Dataset.purge() function.
    This will update the Dataset table, setting Dataset.deleted to 't', Dataset.purged to 't', and
    Dataset.file_size to 0.  The dataset file will then be removed from the file system.
    """
    count = 0
    now = time.time()
    dt = app.model.Dataset.table
    for row in dt.select( ( dt.c.purged=='f' ) & ( dt.c.deleted=='t' ) ).execute():
        last = time.mktime( time.strptime( row.update_time.strftime( '%a %b %d %H:%M:%S %Y' ) ) )
        diff = (now-last)/3600/24 # days
        if diff > days:
            print "Purging dataset id %s" %str( row.id )
            data = app.model.Dataset.get( row.id )
            data.purge()
            data.flush()
            count += 1
    try:
        app.model.flush()
    except:
        pass
    msg = 'Purged %d datasets' % count
    return msg

if __name__ == "__main__":
    main()