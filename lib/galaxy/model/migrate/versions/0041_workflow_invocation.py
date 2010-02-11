"""
Migration script to create tables for tracking workflow invocations.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
logging.basicConfig( level=logging.DEBUG )
log = logging.getLogger( __name__ )

import datetime
now = datetime.datetime.utcnow

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

WorkflowInvocation_table = Table( "workflow_invocation", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "workflow_id", Integer, ForeignKey( "workflow.id" ), index=True, nullable=False )
    )

WorkflowInvocationStep_table = Table( "workflow_invocation_step", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "workflow_invocation_id", Integer, ForeignKey( "workflow_invocation.id" ), index=True, nullable=False ),
    Column( "workflow_step_id",  Integer, ForeignKey( "workflow_step.id" ), index=True, nullable=False ),
    Column( "job_id",  Integer, ForeignKey( "job.id" ), index=True, nullable=False )
    )

tables = [ WorkflowInvocation_table, WorkflowInvocationStep_table ]
    
def upgrade():
    print __doc__
    metadata.reflect()

    for table in tables:
        try:
            table.create()
        except:
            log.warn( "Failed to create table '%s', ignoring (might result in wrong schema)" % table.name )
        
def downgrade():
    metadata.reflect()

    for table in tables:
        table.drop()