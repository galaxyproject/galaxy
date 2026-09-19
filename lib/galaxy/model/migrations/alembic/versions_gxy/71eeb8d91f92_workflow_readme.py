"""Implement fields needed for a workflow readme & help.

Revision ID: 71eeb8d91f92
Revises: a4c3ef999ab5
Create Date: 2025-02-11 11:57:14.477337

"""

import sqlalchemy as sa

from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

workflow_table_name = "workflow"

# revision identifiers, used by Alembic.
revision = "71eeb8d91f92"
down_revision = "a4c3ef999ab5"
branch_labels = None
depends_on = None


def upgrade():
    add_column(workflow_table_name, sa.Column("readme", sa.Text, nullable=True))
    add_column(workflow_table_name, sa.Column("help", sa.Text, nullable=True))
    add_column(workflow_table_name, sa.Column("logo_url", sa.Text, nullable=True))


def downgrade():
    drop_column(workflow_table_name, "readme")
    drop_column(workflow_table_name, "help")
    drop_column(workflow_table_name, "logo_url")
