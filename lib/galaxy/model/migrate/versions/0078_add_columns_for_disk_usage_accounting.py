"""
Migration script to add 'total_size' column to the dataset table, 'purged'
column to the HDA table, and 'disk_usage' column to the User and GalaxySession
tables.
"""

import logging

from sqlalchemy import Boolean, Column, MetaData, Numeric, Table

from galaxy.model.migrate.versions.util import add_column, drop_column

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    c = Column('total_size', Numeric(15, 0))
    add_column(c, 'dataset', metadata)

    HistoryDatasetAssociation_table = Table("history_dataset_association", metadata, autoload=True)
    c = Column("purged", Boolean, index=True, default=False)
    add_column(c, HistoryDatasetAssociation_table, metadata, index_name="ix_history_dataset_association_purged")
    try:
        migrate_engine.execute(HistoryDatasetAssociation_table.update().values(purged=False))
    except Exception:
        log.exception("Updating column 'purged' of table 'history_dataset_association' failed.")

    c = Column('disk_usage', Numeric(15, 0), index=True)
    add_column(c, 'galaxy_user', metadata, index_name="ix_galaxy_user_disk_usage")

    c = Column('disk_usage', Numeric(15, 0), index=True)
    add_column(c, 'galaxy_session', metadata, index_name="ix_galaxy_session_disk_usage")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('disk_usage', 'galaxy_session', metadata)
    drop_column('disk_usage', 'galaxy_user', metadata)

    # SQLAlchemy Migrate has a bug when dropping a boolean column in SQLite
    if migrate_engine.name != 'sqlite':
        drop_column('purged', 'history_dataset_association', metadata)

    drop_column('total_size', 'dataset', metadata)
