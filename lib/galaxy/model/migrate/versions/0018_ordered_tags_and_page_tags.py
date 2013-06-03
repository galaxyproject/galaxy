"""
This migration script provides support for (a) ordering tags by recency and
(b) tagging pages. This script deletes all existing tags.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import *
from migrate import *
import migrate.changeset

import datetime
now = datetime.datetime.utcnow

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()

def display_migration_details():
    print ""
    print "This migration script provides support for (a) ordering tags by recency and"
    print "(b) tagging pages. This script deletes all existing tags."

HistoryTagAssociation_table = Table( "history_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

DatasetTagAssociation_table = Table( "dataset_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

HistoryDatasetAssociationTagAssociation_table = Table( "history_dataset_association_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

PageTagAssociation_table = Table( "page_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    display_migration_details()
    metadata.reflect()

    #
    # Recreate tables.
    #
    try:
        HistoryTagAssociation_table.drop()
        HistoryTagAssociation_table.create()
    except Exception, e:
        print "Recreating history_tag_association table failed: %s" % str( e )
        log.debug( "Recreating history_tag_association table failed: %s" % str( e ) )

    try:
        DatasetTagAssociation_table.drop()
        DatasetTagAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Recreating dataset_tag_association table failed: %s" % str( e ) )

    try:
        HistoryDatasetAssociationTagAssociation_table.drop()
        HistoryDatasetAssociationTagAssociation_table.create()
    except OperationalError, e:
        # Handle error that results from and index name that is too long; this occurs
        # in MySQL.
        if str(e).find("CREATE INDEX") != -1:
            # Manually create index.
            i = Index( "ix_hda_ta_history_dataset_association_id", HistoryDatasetAssociationTagAssociation_table.c.history_dataset_association_id )
            try:
                i.create()
            except Exception, e:
                print str(e)
                log.debug( "Adding index 'ix_hda_ta_history_dataset_association_id' to table 'history_dataset_association_tag_association' table failed: %s" % str( e ) )
    except Exception, e:
        print str(e)
        log.debug( "Recreating history_dataset_association_tag_association table failed: %s" % str( e ) )

    # Create page_tag_association table.
    try:
        PageTagAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating page_tag_association table failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # No need to downgrade other tagging tables. They work fine with verision 16 code.

    # Drop page_tag_association table.
    try:
        PageTagAssociation_table.drop()
    except Exception, e:
        print str(e)
        log.debug( "Dropping page_tag_association table failed: %s" % str( e ) )
