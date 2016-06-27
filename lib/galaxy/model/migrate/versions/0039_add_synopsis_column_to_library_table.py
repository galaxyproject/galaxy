"""
Migration script to add a synopsis column to the library table.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, MetaData, Table, TEXT

log = logging.getLogger( __name__ )
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    Library_table = Table( "library", metadata, autoload=True )
    c = Column( "synopsis", TEXT )
    c.create( Library_table )
    assert c is Library_table.c.synopsis


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    pass
