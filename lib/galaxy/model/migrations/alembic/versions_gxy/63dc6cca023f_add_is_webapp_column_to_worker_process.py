"""Add app_type column to worker_process

Revision ID: 63dc6cca023f
Revises: cd26484899fb
Create Date: 2025-12-09 20:58:13.954728

"""

from sqlalchemy import (
    Column,
    String,
)

from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "63dc6cca023f"
down_revision = "cd26484899fb"
branch_labels = None
depends_on = None

table_name = "worker_process"
column_name = "app_type"


def upgrade():
    add_column(table_name, Column(column_name, String))


def downgrade():
    drop_column(table_name, column_name)
