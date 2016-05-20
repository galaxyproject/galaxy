"""
Migration script to create the repository_role_association table, insert name-spaced
repository administrative roles into the role table and associate each repository and
owner with the appropriate name-spaced role.
"""
import datetime
import logging
import sys

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Table
from sqlalchemy.exc import NoSuchTableError

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()

NOW = datetime.datetime.utcnow
ROLE_TYPE = 'system'

RepositoryRoleAssociation_table = Table( "repository_role_association", metadata,
                                         Column( "id", Integer, primary_key=True ),
                                         Column( "repository_id", Integer, ForeignKey( "repository.id" ), index=True ),
                                         Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
                                         Column( "create_time", DateTime, default=NOW ),
                                         Column( "update_time", DateTime, default=NOW, onupdate=NOW ) )


def nextval( migrate_engine, table, col='id' ):
    if migrate_engine.name in [ 'postgresql', 'postgres' ]:
        return "nextval('%s_%s_seq')" % ( table, col )
    elif migrate_engine.name in [ 'mysql', 'sqlite' ]:
        return "null"
    else:
        raise Exception( 'Unable to convert data for unknown database type: %s' % migrate_engine.name )


def localtimestamp( migrate_engine ):
    if migrate_engine.name in [ 'postgresql', 'postgres', 'mysql' ]:
        return "LOCALTIMESTAMP"
    elif migrate_engine.name == 'sqlite':
        return "current_date || ' ' || current_time"
    else:
        raise Exception( 'Unable to convert data for unknown database type: %s' % migrate_engine.name )


def boolean_false( migrate_engine ):
    if migrate_engine.name in [ 'postgresql', 'postgres', 'mysql' ]:
        return False
    elif migrate_engine.name == 'sqlite':
        return 0
    else:
        raise Exception( 'Unable to convert data for unknown database type: %s' % migrate_engine.name )


def upgrade( migrate_engine ):
    print __doc__
    metadata.bind = migrate_engine
    metadata.reflect()
    # Create the new repository_role_association table.
    try:
        RepositoryRoleAssociation_table.create()
    except Exception as e:
        print str(e)
        log.debug( "Creating repository_role_association table failed: %s" % str( e ) )
    # Select the list of repositories and associated public user names for their owners.
    user_ids = []
    repository_ids = []
    role_names = []
    cmd = 'SELECT repository.id, repository.name, repository.user_id, galaxy_user.username FROM repository, galaxy_user WHERE repository.user_id = galaxy_user.id;'
    for row in migrate_engine.execute( cmd ):
        repository_id = row[ 0 ]
        name = row[ 1 ]
        user_id = row[ 2 ]
        username = row[ 3 ]
        repository_ids.append( int( repository_id ) )
        role_names.append( '%s_%s_admin' % ( str( name ), str( username ) ) )
        user_ids.append( int( user_id ) )
    # Insert a new record into the role table for each new role.
    for tup in zip( repository_ids, user_ids, role_names ):
        repository_id, user_id, role_name = tup
        cmd = "INSERT INTO role VALUES ("
        cmd += "%s, " % nextval( migrate_engine, 'role' )
        cmd += "%s, " % localtimestamp( migrate_engine )
        cmd += "%s, " % localtimestamp( migrate_engine )
        cmd += "'%s', " % role_name
        cmd += "'A user or group member with this role can administer this repository.', "
        cmd += "'%s', " % ROLE_TYPE
        cmd += "%s" % boolean_false( migrate_engine )
        cmd += ");"
        migrate_engine.execute( cmd )
        # Get the id of the new role.
        cmd = "SELECT id FROM role WHERE name = '%s' and type = '%s';" % ( role_name, ROLE_TYPE )
        row = migrate_engine.execute( cmd ).fetchone()
        if row:
            role_id = row[ 0 ]
        else:
            role_id = None
        if role_id:
            # Create a repository_role_association record to associate the repository with the new role.
            cmd = "INSERT INTO repository_role_association VALUES ("
            cmd += "%s, " % nextval( migrate_engine, 'repository_role_association' )
            cmd += "%d, " % int( repository_id )
            cmd += "%d, " % int( role_id )
            cmd += "%s, " % localtimestamp( migrate_engine )
            cmd += "%s " % localtimestamp( migrate_engine )
            cmd += ");"
            migrate_engine.execute( cmd )
            # Create a user_role_association record to associate the repository owner with the new role.
            cmd = "INSERT INTO user_role_association VALUES ("
            cmd += "%s, " % nextval( migrate_engine, 'user_role_association' )
            cmd += "%d, " % int( user_id )
            cmd += "%d, " % int( role_id )
            cmd += "%s, " % localtimestamp( migrate_engine )
            cmd += "%s " % localtimestamp( migrate_engine )
            cmd += ");"
            migrate_engine.execute( cmd )


def downgrade( migrate_engine ):
    metadata.bind = migrate_engine
    metadata.reflect()
    # Determine the list of roles to delete by first selecting the list of repositories and associated
    # public user names for their owners.
    role_names = []
    cmd = 'SELECT name, username FROM repository, galaxy_user WHERE repository.user_id = galaxy_user.id;'
    for row in migrate_engine.execute( cmd ):
        name = row[ 0 ]
        username = row[ 1 ]
        role_names.append( '%s_%s_admin' % ( str( name ), str( username ) ) )
    # Delete each role as well as all users associated with each role.
    for role_name in role_names:
        # Select the id of the record associated with the current role_name from the role table.
        cmd = "SELECT id, name FROM role WHERE name = '%s';" % role_name
        row = migrate_engine.execute( cmd ).fetchone()
        if row:
            role_id = row[ 0 ]
        else:
            role_id = None
        if role_id:
            # Delete all user_role_association records for the current role.
            cmd = "DELETE FROM user_role_association WHERE role_id = %d;" % int( role_id )
            migrate_engine.execute( cmd )
            # Delete all repository_role_association records for the current role.
            cmd = "DELETE FROM repository_role_association WHERE role_id = %d;" % int( role_id )
            migrate_engine.execute( cmd )
            # Delete the role from the role table.
            cmd = "DELETE FROM role WHERE id = %d;" % int( role_id )
            migrate_engine.execute( cmd )
    # Drop the repository_role_association table.
    try:
        RepositoryRoleAssociation_table = Table( "repository_role_association", metadata, autoload=True )
    except NoSuchTableError:
        log.debug( "Failed loading table repository_role_association" )
    try:
        RepositoryRoleAssociation_table.drop()
    except Exception as e:
        log.debug( "Dropping repository_role_association table failed: %s" % str( e ) )
