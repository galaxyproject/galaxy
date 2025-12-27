"""Add workflow_step_id_path column to workflow_invocation_message table

Revision ID: 312602e3191d
Revises: 75b461a2b24a
Create Date: 2025-12-27 12:00:00.000000
"""

import sqlalchemy as sa

from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "312602e3191d"
down_revision = "75b461a2b24a"
branch_labels = None
depends_on = None

# database object names used in this revision
table_name = "workflow_invocation_message"
column_name = "workflow_step_id_path"


def upgrade():
    column = sa.Column(
        column_name,
        sa.JSON,
        nullable=True,  # Allow nulls for existing rows and backward compatibility
        default=None,  # Default to None if not provided
    )
    add_column(
        table_name,
        column,
    )


def downgrade():
    drop_column(
        table_name,
        column_name,
    )
