"""
Migration script to rename the sequencer information form type to external service information form
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
from sqlalchemy.exc import *

from galaxy.model.custom_types import *

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

def upgrade():
    print __doc__
    metadata.reflect()
    current_form_type = 'Sequencer Information Form'
    new_form_type = "External Service Information Form"
    cmd = "update form_definition set type='%s' where type='%s'" % ( new_form_type, current_form_type )
    db_session.execute( cmd )

        
        
def downgrade():
    metadata.reflect()
    new_form_type = 'Sequencer Information Form'
    current_form_type = "External Service Information Form"
    cmd = "update form_definition set type='%s' where type='%s'" % ( new_form_type, current_form_type )
    db_session.execute( cmd )
