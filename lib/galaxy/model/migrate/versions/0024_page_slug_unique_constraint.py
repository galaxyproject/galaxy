"""
Remove unique constraint from page slugs to allow creating a page with
the same slug as a deleted page.
"""
from __future__ import print_function

import datetime
import logging

from sqlalchemy import Index, MetaData, Table

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    Page_table = Table( "page", metadata, autoload=True )

    try:

        # Sqlite doesn't support .alter, so we need to drop an recreate

        i = Index( "ix_page_slug", Page_table.c.slug )
        i.drop()

        i = Index( "ix_page_slug", Page_table.c.slug, unique=False )
        i.create()

    except:

        # Mysql doesn't have a named index, but alter should work

        Page_table.c.slug.alter( unique=False )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
