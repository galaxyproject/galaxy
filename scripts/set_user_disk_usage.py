#!/usr/bin/env python

import os, sys
from ConfigParser import ConfigParser
from optparse import OptionParser

default_config = os.path.abspath( os.path.join( os.path.dirname( __file__ ), '..', 'config/galaxy.ini') )

parser = OptionParser()
parser.add_option( '-c', '--config', dest='config', help='Path to Galaxy config file (config/galaxy.ini)', default=default_config )
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

    sys.path.append( os.path.join( os.path.dirname( __file__ ), '..', 'lib' ) )

    from galaxy import eggs
    import pkg_resources

    import galaxy.config
    from galaxy.objectstore import build_object_store_from_config

    # lazy
    globals()['nice_size'] = __import__( 'galaxy.util', globals(), locals(), ( 'nice_size', ) ).nice_size

    config_parser = ConfigParser( dict( here = os.getcwd(),
                                        database_connection = 'sqlite:///database/universe.sqlite?isolation_level=IMMEDIATE' ) )
    config_parser.read( options.config )

    config_dict = {}
    for key, value in config_parser.items( "app:main" ):
        config_dict[key] = value

    config = galaxy.config.Configuration( **config_dict )
    object_store = build_object_store_from_config( config )

    from galaxy.model import mapping

    return mapping.init( config.file_path, config.database_connection, create_tables = False, object_store = object_store ), object_store, config.database_connection.split(':')[0]

def pgcalc( sa_session, id ):
    sql = """
           UPDATE galaxy_user
              SET disk_usage = (SELECT COALESCE(SUM(total_size), 0)
                                  FROM (  SELECT DISTINCT ON (d.id) d.total_size, d.id
                                            FROM history_dataset_association hda
                                                 JOIN history h ON h.id = hda.history_id
                                                 JOIN dataset d ON hda.dataset_id = d.id
                                           WHERE h.user_id = :id
                                                 AND h.purged = false
                                                 AND hda.purged = false
                                                 AND d.purged = false
                                                 AND d.id NOT IN (SELECT dataset_id
                                                                    FROM library_dataset_dataset_association)
                                         ) sizes)
            WHERE id = :id
        RETURNING disk_usage;
    """
    r = sa_session.execute(sql, {'id':id})
    new = r.fetchone()[0]
    if options.dryrun:
        sa_session.rollback()
    return new

def quotacheck( sa_session, users, engine ):
    sa_session.refresh( user )
    current = user.get_disk_usage()
    print user.username, '<' + user.email + '>:',
    if engine not in ( 'postgres', 'postgresql' ):
        new = user.calculate_disk_usage()
        sa_session.refresh( user )
        # usage changed while calculating, do it again
        if user.get_disk_usage() != current:
            print 'usage changed while calculating, trying again...'
            return quotacheck( sa_session, user, engine )
    else:
        new = pgcalc( sa_session, user.id )
    # yes, still a small race condition between here and the flush
    print 'old usage:', nice_size( current ), 'change:',
    if new in ( current, None ):
        print 'none'
    else:
        if new > current:
            print '+%s' % ( nice_size( new - current ) )
        else:
            print '-%s' % ( nice_size( current - new ) )
        if not options.dryrun and engine not in ( 'postgres', 'postgresql' ):
            user.set_disk_usage( new )
            sa_session.add( user )
            sa_session.flush()

if __name__ == '__main__':
    print 'Loading Galaxy model...'
    model, object_store, engine = init()
    sa_session = model.context.current

    if not options.username and not options.email:
        user_count = sa_session.query( model.User ).count()
        print 'Processing %i users...' % user_count
        for i, user in enumerate( sa_session.query( model.User ).enable_eagerloads( False ).yield_per( 1000 ) ):
            print '%3i%%' % int( float(i) / user_count * 100 ),
            quotacheck( sa_session, user, engine )
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
    quotacheck( sa_session, user, engine )
