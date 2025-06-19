"""Add requested_transform column to dataset_source table

Revision ID: fb16d09348db
Revises: c716ee82337b
Create Date: 2025-06-11 08:48:10.124300
"""

import sqlalchemy as sa

from galaxy.model.custom_types import MutableJSONType
from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "fb16d09348db"
down_revision = "c716ee82337b"
branch_labels = None
depends_on = None

# database object names used in this revision
table_name = "dataset_source"
column_name = "requested_transform"


def upgrade():
    column = sa.Column(
        column_name,
        MutableJSONType,
        nullable=True,  # Allow nulls for existing rows
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
