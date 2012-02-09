#!/usr/bin/env python

import os, sys
from ConfigParser import ConfigParser
from optparse import OptionParser

default_config = os.path.abspath( os.path.join( os.path.dirname( __file__ ), '..', 'universe_wsgi.ini') )

parser = OptionParser()
parser.add_option( '-c', '--config', dest='config', help='Path to Galaxy config file (universe_wsgi.ini)', default=default_config )
parser.add_option( '-u', '--username', dest='username', help='Username of user to update', default='all' )
parser.add_option( '-e', '--email', dest='email', help='Email address of user to update', default='all' )
parser.add_option( '--dry-run', dest='dryrun', help='Dry run (show changes but do not save to database)', action='store_true', default=False )
( options, args ) = parser.parse_args()

def init():

    options.config = os.path.abspath( options.config )
    if options.username == 'all':
        options.username = None
    if options.email == 'all':
        options.email = None

    os.chdir( os.path.dirname( options.config ) )
    sys.path.append( 'lib' )

    from galaxy import eggs
    import pkg_resources

    import galaxy.config
    from galaxy.objectstore import build_object_store_from_config

    config_parser = ConfigParser( dict( here = os.getcwd(),
                                        database_connection = 'sqlite:///database/universe.sqlite?isolation_level=IMMEDIATE' ) )
    config_parser.read( os.path.basename( options.config ) )

    config_dict = {}
    for key, value in config_parser.items( "app:main" ):
        config_dict[key] = value

    config = galaxy.config.Configuration( **config_dict )
    object_store = build_object_store_from_config( config )

    from galaxy.model import mapping

    return mapping.init( config.file_path, config.database_connection, create_tables = False, object_store = object_store ), object_store

def quotacheck( sa_session, users ):
    sa_session.refresh( user )
    current = user.get_disk_usage()
    print user.username, '<' + user.email + '> old usage:', str( current ) + ',',
    new = user.calculate_disk_usage()
    sa_session.refresh( user )
    # usage changed while calculating, do it again
    if user.get_disk_usage() != current:
        print 'usage changed while calculating, trying again...'
        return quotacheck( sa_session, user )
    # yes, still a small race condition between here and the flush
    if new == current:
        print 'no change'
    else:
        print 'new usage:', new
        if not options.dryrun:
            user.set_disk_usage( new )
            sa_session.add( user )
            sa_session.flush()

if __name__ == '__main__':
    print 'Loading Galaxy model...'
    model, object_store = init()
    sa_session = model.context.current

    if not options.username and not options.email:
        user_count = sa_session.query( model.User ).count()
        print 'Processing %i users...' % user_count
        for i, user in enumerate( sa_session.query( model.User ).enable_eagerloads( False ).yield_per( 1000 ) ):
            print '%3i%%' % int( float(i) / user_count * 100 ),
            quotacheck( sa_session, user )
        print '100% complete'
        object_store.shutdown()
        sys.exit( 0 )
    elif options.username:
        user = sa_session.query( model.User ).enable_eagerloads( False ).filter_by( username=options.username ).first()
    elif options.email:
        user = sa_session.query( model.User ).enable_eagerloads( False ).filter_by( email=options.email ).first()
    if not user:
        print 'User not found'
        sys.exit( 1 )
    object_store.shutdown()
    quotacheck( sa_session, user )
