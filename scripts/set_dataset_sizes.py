#!/usr/bin/env python
import os
import sys
from ConfigParser import ConfigParser
from optparse import OptionParser


sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

import galaxy.config
from galaxy.model import mapping
from galaxy.objectstore import build_object_store_from_config
default_config = os.path.abspath( os.path.join( os.path.dirname( __file__ ), os.pardir, 'config/galaxy.ini') )

parser = OptionParser()
parser.add_option( '-c', '--config', dest='config', help='Path to Galaxy config file (config/galaxy.ini)', default=default_config )
( options, args ) = parser.parse_args()


def init():
    options.config = os.path.abspath( options.config )

    config_parser = ConfigParser( dict( here=os.getcwd(),
                                        database_connection='sqlite:///database/universe.sqlite?isolation_level=IMMEDIATE' ) )
    config_parser.read( options.config )

    config_dict = {}
    for key, value in config_parser.items( "app:main" ):
        config_dict[key] = value

    config = galaxy.config.Configuration( **config_dict )

    object_store = build_object_store_from_config( config )
    return (mapping.init( config.file_path, config.database_connection, create_tables=False, object_store=object_store ),
            object_store)


if __name__ == '__main__':
    print 'Loading Galaxy model...'
    model, object_store = init()
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
    object_store.shutdown()
