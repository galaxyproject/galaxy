#!/usr/bin/env python

import os, sys
from ConfigParser import ConfigParser
from optparse import OptionParser

default_config = os.path.abspath( os.path.join( os.path.dirname( __file__ ), '..', 'config/galaxy.ini') )

parser = OptionParser()
parser.add_option( '-c', '--config', dest='config', help='Path to Galaxy config file (config/galaxy.ini)', default=default_config )
( options, args ) = parser.parse_args()

def init():

    options.config = os.path.abspath( options.config )
    sys.path.append( os.path.join( os.path.dirname( __file__ ), '..', 'lib' ) )

    from galaxy import eggs
    import pkg_resources

    config = ConfigParser( dict( file_path = 'database/files',
                                 database_connection = 'sqlite:///database/universe.sqlite?isolation_level=IMMEDIATE' ) )
    config.read( options.config )

    from galaxy.model import mapping

    return mapping.init( config.get( 'app:main', 'file_path' ), config.get( 'app:main', 'database_connection' ), create_tables = False )

if __name__ == '__main__':
    print 'Loading Galaxy model...'
    model = init()
    sa_session = model.context.current

    set = 0
    dataset_count = sa_session.query( model.Dataset ).count()
    print 'Processing %i datasets...' % dataset_count
    percent = 0
    print 'Completed %i%%' % percent,
    sys.stdout.flush()
    for i, dataset in enumerate( sa_session.query( model.Dataset ).enable_eagerloads( False ).yield_per( 1000 ) ):
        if dataset.total_size is None:
            dataset.set_total_size()
            set += 1
            if not set % 1000:
                sa_session.flush()
        new_percent = int( float(i) / dataset_count * 100 )
        if new_percent != percent:
            percent = new_percent
            print '\rCompleted %i%%' % percent,
            sys.stdout.flush()
    sa_session.flush()
    print 'Completed 100%%'
