"""
Drop and readd workflow invocation tables, allowing null jobs
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

def upgrade():
    print __doc__
    
    metadata = MetaData( migrate_engine )
    db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )
    metadata.reflect()

    # 1) Drop

    for table_name in [ "workflow_invocation_step", "workflow_invocation" ]:
        try:
            t = Table( table_name, metadata, autoload=True ).drop()
        except:
            log.exception( "Failed to drop table '%s', ignoring (might result in wrong schema)" % table_name )
        
    # 2) Readd
    
    metadata = MetaData( migrate_engine )
    db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )
    metadata.reflect()
        
    WorkflowInvocation_table = Table( "workflow_invocation", metadata,
        Column( "id", Integer, primary_key=True ),
        Column( "create_time", DateTime, default=now ),
        Column( "update_time", DateTime, default=now, onupdate=now ),
        Column( "workflow_id", Integer, ForeignKey( "workflow.id" ), index=True, nullable=False ),
    )

    WorkflowInvocationStep_table = Table( "workflow_invocation_step", metadata,
        Column( "id", Integer, primary_key=True ),
        Column( "create_time", DateTime, default=now ),
        Column( "update_time", DateTime, default=now, onupdate=now ),
        Column( "workflow_invocation_id", Integer, ForeignKey( "workflow_invocation.id" ), index=True, nullable=False ),
        Column( "workflow_step_id",  Integer, ForeignKey( "workflow_step.id" ), index=True, nullable=False ),
        Column( "job_id",  Integer, ForeignKey( "job.id" ), index=True, nullable=True ),
    )
    
    for table in [ WorkflowInvocation_table, WorkflowInvocationStep_table ]:
        try:
            table.create()
        except:
            log.exception( "Failed to create table '%s', ignoring (might result in wrong schema)" % table.name )

def downgrade():
    # No downgrade
    pass