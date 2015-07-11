"""
This script fixes a problem introduced in 0010_hda_display_at_atuhz_table.py.  MySQL has a
name length limit and thus the index "ix_hdadaa_history_dataset_association_id" has to be
manually created.
"""
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import *
from migrate import *
from migrate.changeset import *

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

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

metadata = MetaData()

def display_migration_details():
    print "========================================"
    print "This script fixes a problem introduced in the previous migration script ( 9->10 ).  MySQL"
    print "has a name length limit and thus the index 'ix_hdadaa_history_dataset_association_id' has"
    print "to be manually created."
    print "========================================"

HistoryDatasetAssociationDisplayAtAuthorization_table = Table( "history_dataset_association_display_at_authorization", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "site", TrimmedString( 255 ) ) )

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    display_migration_details()
    if migrate_engine.name == 'mysql':
        # Load existing tables
        metadata.reflect()
        i = Index( "ix_hdadaa_history_dataset_association_id", HistoryDatasetAssociationDisplayAtAuthorization_table.c.history_dataset_association_id )
        try:
            i.create()
        except Exception, e:
            log.debug( "Adding index 'ix_hdadaa_history_dataset_association_id' to table 'history_dataset_association_display_at_authorization' table failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    if migrate_engine.name == 'mysql':
        # Load existing tables
        metadata.reflect()
        i = Index( "ix_hdadaa_history_dataset_association_id", HistoryDatasetAssociationDisplayAtAuthorization_table.c.history_dataset_association_id )
        try:
            i.drop()
        except Exception, e:
            log.debug( "Removing index 'ix_hdadaa_history_dataset_association_id' from table 'history_dataset_association_display_at_authorization' table failed: %s" % str( e ) )
