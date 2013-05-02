"""
This migration script adds the history_dataset_association_display_at_authorization table,
which allows 'private' datasets to be displayed at external sites without making them public.
If using mysql, this script will display the following error, which is corrected in the next
migration script:

history_dataset_association_display_at_authorization table failed:  (OperationalError)
(1059, "Identifier name  'ix_history_dataset_association_display_at_authorization_update_time'
is too long
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
    print "This migration script adds the history_dataset_association_display_at_authorization table, which"
    print "allows 'private' datasets to be displayed at external sites without making them public."
    print ""
    print "If using mysql, this script will display the following error, which is corrected in the next migration"
    print "script: history_dataset_association_display_at_authorization table failed:  (OperationalError)"
    print "(1059, 'Identifier name  'ix_history_dataset_association_display_at_authorization_update_time'"
    print "is too long."
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
    # Load existing tables
    metadata.reflect()
    try:
        HistoryDatasetAssociationDisplayAtAuthorization_table.create()
    except Exception, e:
        log.debug( "Creating history_dataset_association_display_at_authorization table failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    # Load existing tables
    metadata.reflect()
    try:
        HistoryDatasetAssociationDisplayAtAuthorization_table.drop()
    except Exception, e:
        log.debug( "Dropping history_dataset_association_display_at_authorization table failed: %s" % str( e ) )
