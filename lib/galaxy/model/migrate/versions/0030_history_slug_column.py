"""
Migration script to add column for a history slug.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, Index, MetaData, Table, TEXT

log = logging.getLogger( __name__ )
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine

    print(__doc__)
    metadata.reflect()

    History_table = Table( "history", metadata, autoload=True )

    # Mysql needs manual index creation because of max length index.
    if migrate_engine.name != 'mysql':
        # Create slug column.
        c = Column( "slug", TEXT, index=True )
        c.create( History_table, index_name='ix_history_slug')
    else:
        c = Column( "slug", TEXT )
        c.create( History_table, index_name='')
        i = Index( "ix_history_slug", History_table.c.slug, mysql_length=200)
        i.create()
    assert c is History_table.c.slug


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    History_table = Table( "history", metadata, autoload=True )
    History_table.c.slug.drop()
