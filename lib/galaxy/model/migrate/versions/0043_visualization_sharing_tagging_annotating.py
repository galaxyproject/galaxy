"""
Migration script to create tables and columns for sharing visualizations.
"""
from __future__ import print_function

import logging

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, MetaData, Table, TEXT, Unicode

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

VisualizationAnnotationAssociation_table = Table("visualization_annotation_association", metadata,
                                                 Column("id", Integer, primary_key=True),
                                                 Column("visualization_id", Integer, ForeignKey("visualization.id"), index=True),
                                                 Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                                 Column("annotation", TEXT, index=False))


def engine_false(migrate_engine):
    if migrate_engine.name in ['postgres', 'postgresql']:
        return "FALSE"
    elif migrate_engine.name in ['mysql', 'sqlite']:
        return 0
    else:
        raise Exception('Unknown database type: %s' % migrate_engine.name)


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    Visualiation_table = Table("visualization", metadata, autoload=True)
    # Create visualization_user_share_association table.
    try:
        VisualizationUserShareAssociation_table.create()
    except Exception:
        log.exception("Creating visualization_user_share_association table failed.")

    # Add columns & create indices for supporting sharing to visualization table.
    deleted_column = Column("deleted", Boolean, default=False, index=True)
    importable_column = Column("importable", Boolean, default=False, index=True)
    slug_column = Column("slug", TEXT)
    published_column = Column("published", Boolean, index=True)

    try:
        # Add column.
        deleted_column.create(Visualiation_table, index_name="ix_visualization_deleted")
        assert deleted_column is Visualiation_table.c.deleted

        # Fill column with default value.
        cmd = "UPDATE visualization SET deleted = %s" % engine_false(migrate_engine)
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Adding deleted column to visualization table failed.")

    try:
        # Add column.
        importable_column.create(Visualiation_table, index_name='ix_visualization_importable')
        assert importable_column is Visualiation_table.c.importable

        # Fill column with default value.
        cmd = "UPDATE visualization SET importable = %s" % engine_false(migrate_engine)
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Adding importable column to visualization table failed.")

    try:
        slug_column.create(Visualiation_table)
        assert slug_column is Visualiation_table.c.slug
    except Exception:
        log.exception("Adding slug column to visualization table failed.")

    try:
        if migrate_engine.name == 'mysql':
            # Have to create index manually.
            cmd = "CREATE INDEX ix_visualization_slug ON visualization ( slug ( 100 ) )"
            migrate_engine.execute(cmd)
        else:
            i = Index("ix_visualization_slug", Visualiation_table.c.slug)
            i.create()
    except Exception:
        log.exception("Adding index 'ix_visualization_slug' failed.")

    try:
        # Add column.
        published_column.create(Visualiation_table, index_name='ix_visualization_published')
        assert published_column is Visualiation_table.c.published

        # Fill column with default value.
        cmd = "UPDATE visualization SET published = %s" % engine_false(migrate_engine)
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Adding published column to visualization table failed.")

    # Create visualization_tag_association table.
    try:
        VisualizationTagAssociation_table.create()
    except Exception:
        log.exception("Creating visualization_tag_association table failed.")

    # Create visualization_annotation_association table.
    try:
        VisualizationAnnotationAssociation_table.create()
    except Exception:
        log.exception("Creating visualization_annotation_association table failed.")

    # Need to create index for visualization annotation manually to deal with errors.
    try:
        if migrate_engine.name == 'mysql':
            # Have to create index manually.
            cmd = "CREATE INDEX ix_visualization_annotation_association_annotation ON visualization_annotation_association ( annotation ( 100 ) )"
            migrate_engine.execute(cmd)
        else:
            i = Index("ix_visualization_annotation_association_annotation", VisualizationAnnotationAssociation_table.c.annotation)
            i.create()
    except Exception:
        log.exception("Adding index 'ix_visualization_annotation_association_annotation' failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    Visualiation_table = Table("visualization", metadata, autoload=True)
    # Drop visualization_user_share_association table.
    try:
        VisualizationUserShareAssociation_table.drop()
    except Exception:
        log.exception("Dropping visualization_user_share_association table failed.")

    # Drop columns for supporting sharing from visualization table.
    try:
        Visualiation_table.c.deleted.drop()
    except Exception:
        log.exception("Dropping deleted column from visualization table failed.")

    try:
        Visualiation_table.c.importable.drop()
    except Exception:
        log.exception("Dropping importable column from visualization table failed.")

    try:
        Visualiation_table.c.slug.drop()
    except Exception:
        log.exception("Dropping slug column from visualization table failed.")

    try:
        Visualiation_table.c.published.drop()
    except Exception:
        log.exception("Dropping published column from visualization table failed.")

    # Drop visualization_tag_association table.
    try:
        VisualizationTagAssociation_table.drop()
    except Exception:
        log.exception("Dropping visualization_tag_association table failed.")

    # Drop visualization_annotation_association table.
    try:
        VisualizationAnnotationAssociation_table.drop()
    except Exception:
        log.exception("Dropping visualization_annotation_association table failed.")
