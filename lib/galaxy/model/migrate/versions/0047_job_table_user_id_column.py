"""
Add a user_id column to the job table.
"""

from sqlalchemy import *
from migrate import *
from migrate.changeset import *
from galaxy.model.custom_types import *

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )

def upgrade():
    print __doc__
    metadata.reflect()
    try:
        Job_table = Table( "job", metadata, autoload=True )
    except NoSuchTableError:
        Job_table = None
        log.error( "Failed loading table job" )
    if Job_table:
        try:
            col = Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=True )
            col.create( Job_table )
            assert col is Job_table.c.user_id
        except Exception, e:
            log.error( "Adding column 'user_id' to job table failed: %s" % ( str( e ) ) )
        try:
            i = Index( "ix_job_user_id", Job_table.c.user_id )
            i.create()
        except Exception, e:
            log.error( "Adding index 'ix_job_user_id' failed: %s" % str( e ) )

def downgrade():
    metadata.reflect()
    try:
        Job_table = Table( "job", metadata, autoload=True )
    except NoSuchTableError:
        Job_table = None
        log.error( "Failed loading table job" )
    if Job_table:
        try:
            col = Job_table.c.user_id
            col.drop()
        except Exception, e:
            log.error( "Dropping column 'user_id' from job table failed: %s" % ( str( e ) ) )
