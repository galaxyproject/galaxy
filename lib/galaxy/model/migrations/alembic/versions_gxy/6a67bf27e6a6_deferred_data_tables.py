"""deferred data tables

Revision ID: 6a67bf27e6a6
Revises: b182f655505f
Create Date: 2022-03-14 12:17:55.313830

"""
from alembic import op
from sqlalchemy import (
    Boolean,
    Column,
)

from galaxy.model.migrations.util import drop_column

# revision identifiers, used by Alembic.
revision = "6a67bf27e6a6"
down_revision = "b182f655505f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("history_dataset_association", Column("metadata_deferred", Boolean(), default=False))
    op.add_column("library_dataset_dataset_association", Column("metadata_deferred", Boolean(), default=False))


def downgrade():
    drop_column("history_dataset_association", "metadata_deferred")
    drop_column("library_dataset_dataset_association", "metadata_deferred")
