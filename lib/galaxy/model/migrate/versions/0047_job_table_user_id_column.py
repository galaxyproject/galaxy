"""
Add a user_id column to the job table.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import *
from migrate import *
from migrate.changeset import *
from galaxy.model.custom_types import *

import datetime
now = datetime.datetime.utcnow

import sys, logging
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()
    try:
        Job_table = Table( "job", metadata, autoload=True )
    except NoSuchTableError:
        Job_table = None
        log.debug( "Failed loading table job" )
    if Job_table is not None:

        if migrate_engine.name != 'sqlite':
            try:
                col = Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=True )
                col.create( Job_table, index_name='ix_job_user_id' )
                assert col is Job_table.c.user_id
            except Exception, e:
                log.debug( "Adding column 'user_id' to job table failed: %s" % ( str( e ) ) )
        else:
            try:
                col = Column( "user_id", Integer, nullable=True)
                col.create( Job_table )
                assert col is Job_table.c.user_id
            except Exception, e:
                log.debug( "Adding column 'user_id' to job table failed: %s" % ( str( e ) ) )
        try:
            cmd = "SELECT job.id AS galaxy_job_id, " \
                + "galaxy_session.user_id AS galaxy_user_id " \
                + "FROM job " \
                + "JOIN galaxy_session ON job.session_id = galaxy_session.id;"
            job_users = migrate_engine.execute( cmd ).fetchall()
            print "Updating user_id column in job table for ", len( job_users ), " rows..."
            print ""
            update_count = 0
            for row in job_users:
                if row.galaxy_user_id:
                    cmd = "UPDATE job SET user_id = %d WHERE id = %d" % ( int( row.galaxy_user_id ), int( row.galaxy_job_id ) )
                    update_count += 1
                migrate_engine.execute( cmd )
            print "Updated the user_id column for ", update_count, " rows in the job table.  "
            print len( job_users ) - update_count, " rows have no user_id since the value was NULL in the galaxy_session table."
            print ""
        except Exception, e:
            log.debug( "Updating job.user_id column failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        Job_table = Table( "job", metadata, autoload=True )
    except NoSuchTableError:
        Job_table = None
        log.debug( "Failed loading table job" )
    if Job_table:
        try:
            col = Job_table.c.user_id
            col.drop()
        except Exception, e:
            log.debug( "Dropping column 'user_id' from job table failed: %s" % ( str( e ) ) )
