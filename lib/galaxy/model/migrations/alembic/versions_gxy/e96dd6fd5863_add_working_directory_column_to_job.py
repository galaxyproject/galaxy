"""add working_directory column to job

Revision ID: e96dd6fd5863
Revises: fb8621b7c075
Create Date: 2026-07-16 14:16:16.929329

"""

from sqlalchemy import (
    Column,
    String,
)

from galaxy.model.migrations.util import (
    add_column,
    column_exists,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "e96dd6fd5863"
down_revision = "fb8621b7c075"
branch_labels = None
depends_on = None

table_name = "job"
column_name = "working_directory"


def upgrade():
    if not column_exists(table_name, column_name, False):
        add_column(table_name, Column(column_name, String(1024)))


def downgrade():
    drop_column(table_name, column_name)
