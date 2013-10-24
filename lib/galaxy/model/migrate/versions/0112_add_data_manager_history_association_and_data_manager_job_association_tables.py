"""
Migration script to add the data_manager_history_association table and data_manager_job_association.
"""
from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
import sys, logging
from galaxy.model.custom_types import *
from sqlalchemy.exc import *
import datetime
now = datetime.datetime.utcnow

log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )


metadata = MetaData()

DataManagerHistoryAssociation_table = Table( "data_manager_history_association", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True )
    )

DataManagerJobAssociation_table = Table( "data_manager_job_association", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "data_manager_id", TEXT, index=True )
    )

def upgrade(migrate_engine):
    print __doc__
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        DataManagerHistoryAssociation_table.create()
        log.debug( "Created data_manager_history_association table" )
    except Exception, e:
        log.debug( "Creating data_manager_history_association table failed: %s" % str( e ) )
    try:
        DataManagerJobAssociation_table.create()
        log.debug( "Created data_manager_job_association table" )
    except Exception, e:
        log.debug( "Creating data_manager_job_association table failed: %s" % str( e ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        DataManagerHistoryAssociation_table.drop()
        log.debug( "Dropped data_manager_history_association table" )
    except Exception, e:
        log.debug( "Dropping data_manager_history_association table failed: %s" % str( e ) )
    try:
        DataManagerJobAssociation_table.drop()
        log.debug( "Dropped data_manager_job_association table" )
    except Exception, e:
        log.debug( "Dropping data_manager_job_association table failed: %s" % str( e ) )
