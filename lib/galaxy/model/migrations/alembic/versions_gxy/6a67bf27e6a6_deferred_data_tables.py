"""deferred data tables

Revision ID: 6a67bf27e6a6
Revises: b182f655505f
Create Date: 2022-03-14 12:17:55.313830

"""
from sqlalchemy import (
    Boolean,
    Column,
)

from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "6a67bf27e6a6"
down_revision = "b182f655505f"
branch_labels = None
depends_on = None

table1_name = "history_dataset_association"
table2_name = "library_dataset_dataset_association"
column = Column("metadata_deferred", Boolean(), default=False)


def upgrade():
    return
    add_column(table1_name, column)
    add_column(table2_name, column)


def downgrade():
    return
    drop_column(table1_name, column.name)
    drop_column(table2_name, column.name)
