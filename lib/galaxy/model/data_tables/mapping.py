"""
Details of how the data model objects are mapped onto the relational database
are encapsulated here.
"""

import logging

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String, Table,
    UniqueConstraint
)
from sqlalchemy.orm import mapper, relation

from galaxy.model import data_tables as data_tables_model
from galaxy.model.base import ModelMapping
from galaxy.model.orm.engine_factory import build_engine
from galaxy.model.orm.now import now

log = logging.getLogger(__name__)

metadata = MetaData()

# Data Table in database tables
data_tables_model.DataTable.table = Table(
    'data_table',
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(255), index=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    UniqueConstraint('name'),
)

data_tables_model.DataTableColumn.table = Table(
    'data_table_column',
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(255), index=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    UniqueConstraint('name'),
)

data_tables_model.DataTableColumnAssociation.table = Table(
    'data_table_column_association',
    metadata,
    Column("id", Integer, primary_key=True),
    Column("data_table_id", Integer, ForeignKey("data_table.id"), index=True),
    Column("data_table_column_id", Integer, ForeignKey("data_table_column.id"), index=True),
)

data_tables_model.DataTableRow.table = Table(
    'data_table_row',
    metadata,
    Column("id", Integer, primary_key=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
)

data_tables_model.DataTableRowAssociation.table = Table(
    'data_table_row_association',
    metadata,
    Column("id", Integer, primary_key=True),
    Column("data_table_id", Integer, ForeignKey("data_table.id"), index=True),
    Column("data_table_row_id", Integer, ForeignKey("data_table_row.id"), index=True),
)

data_tables_model.DataTableField.table = Table(
    'data_table_field',
    metadata,
    Column("id", Integer, primary_key=True),
    Column("value", String(255), index=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    Column("data_table_row_id", Integer, ForeignKey("data_table_row.id"), index=True),
    Column("data_table_column_id", Integer, ForeignKey("data_table_column.id"), index=True),
)

# Data tables
mapper(data_tables_model.DataTable, data_tables_model.DataTable.table, properties={})
mapper(data_tables_model.DataTableColumnAssociation, data_tables_model.DataTableColumnAssociation.table,
       properties=dict(data_table=relation(data_tables_model.DataTable),
                       data_table_column=relation(data_tables_model.DataTableColumn)
                       )
       )
mapper(data_tables_model.DataTableColumn, data_tables_model.DataTableColumn.table, properties={})
mapper(data_tables_model.DataTableRowAssociation, data_tables_model.DataTableRowAssociation.table, properties=dict(
    data_table=relation(data_tables_model.DataTable),
    data_table_row=relation(data_tables_model.DataTableRow)
))
mapper(data_tables_model.DataTableRow, data_tables_model.DataTableRow.table, properties={})
mapper(data_tables_model.DataTableField, data_tables_model.DataTableField.table, properties=dict(
    data_table_row=relation(data_tables_model.DataTableRow),
    data_table_column=relation(data_tables_model.DataTableColumn)
))


def init(url, engine_options=None, create_tables=False):
    """Connect mappings to the database"""
    # Load the appropriate db module
    engine_options = engine_options or {}
    engine = build_engine(url, engine_options)
    # Connect the metadata to the database.
    metadata.bind = engine
    result = ModelMapping([data_tables_model], engine=engine)
    # Create tables if needed
    if create_tables:
        metadata.create_all()
        # metadata.engine.commit()
    result.create_tables = create_tables
    # load local galaxy security policy
    return result
