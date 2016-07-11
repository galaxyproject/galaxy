"""
Migration script to create a new 'sequencer' table
"""
from __future__ import print_function

import datetime
import logging

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, Table, TEXT
from sqlalchemy.exc import NoSuchTableError

from galaxy.model.custom_types import TrimmedString

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
metadata = MetaData()

# Table to add
Sequencer_table = Table( 'sequencer', metadata,
                         Column( "id", Integer, primary_key=True ),
                         Column( "create_time", DateTime, default=now ),
                         Column( "update_time", DateTime, default=now, onupdate=now ),
                         Column( "name", TrimmedString( 255 ), nullable=False ),
                         Column( "description", TEXT ),
                         Column( "sequencer_type_id", TrimmedString( 255 ), nullable=False ),
                         Column( "version", TrimmedString( 255 ) ),
                         Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
                         Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
                         Column( "deleted", Boolean, index=True, default=False ) )


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    # create the sequencer table
    try:
        Sequencer_table.create()
    except Exception as e:
        log.debug( "Creating 'sequencer' table failed: %s" % str( e ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    # delete sequencer table
    try:
        Sequencer_table = Table( "sequencer", metadata, autoload=True )
    except NoSuchTableError:
        Sequencer_table = None
        log.debug( "Failed loading table sequencer" )
    if Sequencer_table:
        try:
            Sequencer_table.drop()
        except Exception as e:
            log.debug( "Deleting 'sequencer' table failed: %s" % str( e ) )
