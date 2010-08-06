"""
Migration script to add the post_job_action_association table.
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

PostJobActionAssociation_table = Table("post_job_action_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("post_job_action_id", Integer, ForeignKey("post_job_action.id"), index=True, nullable=False),
    Column("job_id", Integer, ForeignKey("job.id"), index=True, nullable=False))

def upgrade():
    print __doc__
    metadata.reflect()
    try:
        PostJobActionAssociation_table.create()
    except Exception, e:
        log.debug( "Creating PostJobActionAssociation table failed: %s" % str( e ) )

def downgrade():
    # Load existing tables
    metadata.reflect()
    try:
        PostJobActionAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping PostJobActionAssociation table failed: %s" % str( e ) )
