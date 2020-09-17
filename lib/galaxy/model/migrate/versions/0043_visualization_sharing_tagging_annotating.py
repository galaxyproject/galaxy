"""
Migration script to create tables and columns for sharing visualizations.
"""

import logging

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Table,
    TEXT,
    Unicode
)

from galaxy.model.migrate.versions.util import (
    add_column,
    add_index,
    create_table,
    drop_column,
    drop_table,
    engine_false
)

log = logging.getLogger(__name__)
metadata = MetaData()

# Sharing visualizations.

VisualizationUserShareAssociation_table = Table("visualization_user_share_association", metadata,
                                                Column("id", Integer, primary_key=True),
                                                Column("visualization_id", Integer, ForeignKey("visualization.id"), index=True),
                                                Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True))

# Tagging visualizations.

VisualizationTagAssociation_table = Table("visualization_tag_association", metadata,
                                          Column("id", Integer, primary_key=True),
                                          Column("visualization_id", Integer, ForeignKey("visualization.id"), index=True),
                                          Column("tag_id", Integer, ForeignKey("tag.id"), index=True),
                                          Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                          Column("user_tname", Unicode(255), index=True),
                                          Column("value", Unicode(255), index=True),
                                          Column("user_value", Unicode(255), index=True))

# Annotating visualizations.

VisualizationAnnotationAssociation_table = Table(
    "visualization_annotation_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("visualization_id", Integer, ForeignKey("visualization.id"), index=True),
    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
    Column("annotation", TEXT),
    Index('ix_visualization_annotation_association_annotation', 'annotation', mysql_length=200),
)

TABLES = [
    VisualizationUserShareAssociation_table,
    VisualizationTagAssociation_table,
    VisualizationAnnotationAssociation_table
]


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        create_table(table)

    # Add columns & create indices for supporting sharing to visualization table.
    Visualization_table = Table("visualization", metadata, autoload=True)
    deleted_column = Column("deleted", Boolean, default=False, index=True)
    add_column(deleted_column, Visualization_table, metadata, index_name="ix_visualization_deleted")
    try:
        # Fill column with default value.
        cmd = "UPDATE visualization SET deleted = %s" % engine_false(migrate_engine)
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Updating column 'deleted' of table 'visualization' failed.")

    importable_column = Column("importable", Boolean, default=False, index=True)
    add_column(importable_column, Visualization_table, metadata, index_name='ix_visualization_importable')
    try:
        # Fill column with default value.
        cmd = "UPDATE visualization SET importable = %s" % engine_false(migrate_engine)
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Updating column 'importable' of table 'visualization' failed.")

    slug_column = Column("slug", TEXT)
    add_column(slug_column, Visualization_table, metadata)
    # Index needs to be added separately because MySQL cannot index a TEXT/BLOB
    # column without specifying mysql_length
    add_index('ix_visualization_slug', Visualization_table, 'slug')

    published_column = Column("published", Boolean, index=True)
    add_column(published_column, Visualization_table, metadata, index_name='ix_visualization_published')
    try:
        # Fill column with default value.
        cmd = "UPDATE visualization SET published = %s" % engine_false(migrate_engine)
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Updating column 'published' of table 'visualization' failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    Visualization_table = Table("visualization", metadata, autoload=True)
    drop_column('deleted', Visualization_table)
    drop_column('importable', Visualization_table)
    drop_column('slug', Visualization_table)
    drop_column('published', Visualization_table)

    for table in TABLES:
        drop_table(table)
