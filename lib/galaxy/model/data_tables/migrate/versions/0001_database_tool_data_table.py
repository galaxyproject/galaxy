"""
Add tables for Database Tool Data tables
"""
from __future__ import print_function

import logging

from sqlalchemy import (Column, DateTime, ForeignKey, Integer, MetaData, String, Table, UniqueConstraint)

from galaxy.model.migrate.versions.util import (create_table, drop_table)
from galaxy.model.orm.now import now

log = logging.getLogger(__name__)
metadata = MetaData()


DataTable_table = Table(
    'data_table',
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(255), index=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    UniqueConstraint('name'),
)

DataTableColumn_table = Table(
    'data_table_column',
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(255), index=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    UniqueConstraint("name")
)

DataTableColumnAssociation_table = Table(
    'data_table_column_association',
    metadata,
    Column("id", Integer, primary_key=True),
    Column("data_table_id", Integer, ForeignKey("data_table.id"), index=True),
    Column("data_table_column_id", Integer, ForeignKey("data_table_column.id"), index=True),
)

DataTableRow_table = Table(
    'data_table_row',
    metadata,
    Column("id", Integer, primary_key=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
)

DataTableRowAssociation_table = Table(
    'data_table_row_association',
    metadata,
    Column("id", Integer, primary_key=True),
    Column("data_table_id", Integer, ForeignKey("data_table.id"), index=True),
    Column("data_table_row_id", Integer, ForeignKey("data_table_row.id"), index=True),
)

DataTableField_table = Table(
    'data_table_field',
    metadata,
    Column("id", Integer, primary_key=True),
    Column("value", String(255), index=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    Column("data_table_row_id", Integer, ForeignKey("data_table_row.id"), index=True),
    Column("data_table_column_id", Integer, ForeignKey("data_table_column.id"), index=True),
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(DataTable_table)
    create_table(DataTableColumn_table)
    create_table(DataTableColumnAssociation_table)
    create_table(DataTableRow_table)
    create_table(DataTableField_table)
    create_table(DataTableRowAssociation_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(DataTableRowAssociation_table)
    drop_table(DataTableField_table)
    drop_table(DataTableRow_table)
    drop_table(DataTableColumnAssociation_table)
    drop_table(DataTableColumn_table)
    drop_table(DataTable_table)
