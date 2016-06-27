"""
Migration script to add 'ldda_parent_id' column to the implicitly_converted_dataset_association table.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table

log = logging.getLogger( __name__ )
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    try:
        Implicitly_converted_table = Table( "implicitly_converted_dataset_association", metadata, autoload=True )
        if migrate_engine.name != 'sqlite':
            c = Column( "ldda_parent_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), index=True, nullable=True )
        else:
            # Can't use the ForeignKey in sqlite.
            c = Column( "ldda_parent_id", Integer, index=True, nullable=True )
        c.create( Implicitly_converted_table, index_name="ix_implicitly_converted_dataset_assoc_ldda_parent_id")
        assert c is Implicitly_converted_table.c.ldda_parent_id
    except Exception as e:
        print("Adding ldda_parent_id column to implicitly_converted_dataset_association table failed: %s" % str( e ))
        log.debug( "Adding ldda_parent_id column to implicitly_converted_dataset_association table failed: %s" % str( e ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        Implicitly_converted_table = Table( "implicitly_converted_dataset_association", metadata, autoload=True )
        Implicitly_converted_table.c.ldda_parent_id.drop()
    except Exception as e:
        print("Dropping ldda_parent_id column from implicitly_converted_dataset_association table failed: %s" % str( e ))
        log.debug( "Dropping ldda_parent_id column from implicitly_converted_dataset_association table failed: %s" % str( e ) )
