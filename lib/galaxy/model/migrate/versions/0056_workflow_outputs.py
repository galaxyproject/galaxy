"""
Migration script to create tables for adding explicit workflow outputs.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
logging.basicConfig( level=logging.DEBUG )
log = logging.getLogger( __name__ )

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

WorkflowOutput_table = Table( "workflow_output", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_step_id", Integer, ForeignKey("workflow_step.id"), index=True, nullable=False),
    Column( "output_name", String(255), nullable=True))

tables = [WorkflowOutput_table]

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