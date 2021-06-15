"""
Migration script to create a table for page-user share association.
"""

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table

log = logging.getLogger(__name__)
metadata = MetaData()

PageUserShareAssociation_table = Table("page_user_share_association", metadata,
                                       Column("id", Integer, primary_key=True),
                                       Column("page_id", Integer, ForeignKey("page.id"), index=True),
                                       Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True))


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    # Create stored_workflow_tag_association table.
    try:
        PageUserShareAssociation_table.create()
    except Exception:
        log.exception("Creating page_user_share_association table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop workflow_tag_association table.
    try:
        PageUserShareAssociation_table.drop()
    except Exception:
        log.exception("Dropping page_user_share_association table failed.")
