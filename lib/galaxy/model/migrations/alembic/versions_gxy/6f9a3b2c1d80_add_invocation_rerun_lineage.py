"""Add workflow invocation rerun lineage.

Revision ID: 6f9a3b2c1d80
Revises: 64d49ad328d4
Create Date: 2026-10-15
"""

from sqlalchemy import (
    Column,
    Integer,
)

from galaxy.model.migrations.util import (
    add_column,
    create_foreign_key,
    create_index,
    drop_column,
    drop_constraint,
    drop_index,
)

revision = "6f9a3b2c1d80"
down_revision = "64d49ad328d4"
branch_labels = None
depends_on = None

table_name = "workflow_invocation"
column_name = "rerun_of_invocation_id"
index_name = "ix_workflow_invocation_rerun_of_invocation_id"
foreign_key_name = "workflow_invocation_rerun_of_invocation_id_fkey"


def upgrade():
    add_column(table_name, Column(column_name, Integer, nullable=True))
    create_foreign_key(foreign_key_name, table_name, table_name, [column_name], ["id"], ondelete="SET NULL")
    create_index(index_name, table_name, [column_name])


def downgrade():
    drop_index(index_name, table_name)
    drop_constraint(foreign_key_name, table_name)
    drop_column(table_name, column_name)
