"""
Migration script to (a) create tables for annotating pages.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, TEXT

log = logging.getLogger(__name__)
metadata = MetaData()

PageAnnotationAssociation_table = Table("page_annotation_association", metadata,
                                        Column("id", Integer, primary_key=True),
                                        Column("page_id", Integer, ForeignKey("page.id"), index=True),
                                        Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                        Column("annotation", TEXT, index=True))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # Create history_annotation_association table.
    try:
        PageAnnotationAssociation_table.create()
    except Exception:
        log.exception("Creating page_annotation_association table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop page_annotation_association table.
    try:
        PageAnnotationAssociation_table.drop()
    except Exception:
        log.exception("Dropping page_annotation_association table failed.")
