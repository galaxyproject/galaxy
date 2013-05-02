"""
Migration script to add a 'tool_version' column to the hda/ldda tables.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

from galaxy.model.custom_types import *

metadata = MetaData()

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()
    try:
        hda_table = Table( "history_dataset_association", metadata, autoload=True )
        c = Column( "tool_version", TEXT )
        c.create( hda_table )
        assert c is hda_table.c.tool_version

        ldda_table = Table( "library_dataset_dataset_association", metadata, autoload=True )
        c = Column( "tool_version", TEXT )
        c.create( ldda_table )
        assert c is ldda_table.c.tool_version

    except Exception, e:
        print "Adding the tool_version column to the hda/ldda tables failed: ", str( e )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        hda_table = Table( "history_dataset_association", metadata, autoload=True )
        hda_table.c.tool_version.drop()

        ldda_table = Table( "library_dataset_dataset_association", metadata, autoload=True )
        ldda_table.c.tool_version.drop()
    except Exception, e:
        print "Dropping the tool_version column from hda/ldda table failed: ", str( e )
