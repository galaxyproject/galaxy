"""
Migration script to (a) create tables for annotating pages.
"""

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Table,
    TEXT
)

from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)

log = logging.getLogger(__name__)
metadata = MetaData()

PageAnnotationAssociation_table = Table(
    "page_annotation_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("page_id", Integer, ForeignKey("page.id"), index=True),
    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
    Column("annotation", TEXT),
    Index('ix_page_annotation_association_annotation', 'annotation', mysql_length=200),
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(PageAnnotationAssociation_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(PageAnnotationAssociation_table)
