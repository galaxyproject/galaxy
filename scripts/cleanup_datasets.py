#!/usr/bin/env python2.4
#Dan Blankenberg
"""
Allows dataset cleanup.
"""

import sys, os, time, ConfigParser
from optparse import OptionParser
import galaxy.app

def main():
    parser = OptionParser()
    parser.add_option("-d", "--days", dest="days", action="store", type="int", help="number of days (30)", default=30)
    parser.add_option("-a", "--abandon", action="store_true", dest="abandon", default=False, help="abandon old, unowned (userless) histories")
    parser.add_option("-p", "--purge", action="store_true", dest="purge", default=False, help="purge old deleted datasets")
    (options, args) = parser.parse_args()
    ini_file = args[0]
    
    if not (options.purge ^ options.abandon):
        parser.print_help()
        sys.exit(0)
    
    conf_parser = ConfigParser.ConfigParser({'here':os.getcwd()})
    conf_parser.read(ini_file)
    configuration = {}
    for key, value in conf_parser.items("app:main"): configuration[key] = value
    app = galaxy.app.UniverseApplication( global_conf = ini_file, **configuration )
    msg = None
    if options.purge:
        msg = purge(app, options.days)
    elif options.abandon:
        msg = abandon(app, options.days)
    app.shutdown()
    if msg:
        print
        print "Number of days buffered: %i" % options.days
        print msg
    sys.exit(0)

def abandon( app, days ):
    """ Abandons userless histories older than specified number of days """
    histories_no_users = []
    history_count = 0
    for row in app.model.History.table.select().execute():
        try:
            int(row.user_id)
        except:
            history = app.model.History.get(row.id)
            now  = time.time()
            last = time.mktime( time.strptime( history.update_time.strftime('%a %b %d %H:%M:%S %Y') )) 
            diff = (now - last) /3600/24 # days
            if diff>days:
                histories_no_users.append(row.id)
                if history.deleted: continue #we don't add to history delete count, but we do want to be able to make sure datasets associated with deleted histories are really deleted
                history.deleted = True
                history_count += 1
    
    dataset_count = 0
    for row in app.model.Dataset.table.select().execute():
        if row.history_id in histories_no_users:
            #delete dataset
            data = app.model.Dataset.get(row.id)
            if data.deleted: continue
            data.deleted = True
            dataset_count += 1
    try:
        app.model.flush()
    except:
        pass
    msg = 'deleted %d abandoned histories with %d total datasets' % ( history_count, dataset_count )
    return msg

def purge( app, days ):
    """ Purges deleted datasets older than specified number of days """
    count = 0
    now  = time.time()
    for row in list(app.model.Dataset.table.select().execute()):
        data = app.model.Dataset.get(row.id)
        if data.deleted and not data.purged:
            last = time.mktime( time.strptime( data.update_time.strftime('%a %b %d %H:%M:%S %Y') ))
            diff = (now - last) /3600/24 # days
            if diff>days:
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