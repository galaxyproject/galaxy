"""Add when_expression column

Revision ID: 518c8438a91b
Revises: 59e024ceaca1
Create Date: 2022-10-24 16:43:39.565871

"""
import sqlalchemy as sa

from galaxy.model.custom_types import JSONType
from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "518c8438a91b"
down_revision = "59e024ceaca1"
branch_labels = None
depends_on = None

# database object names used in this revision
table_name = "workflow_step"
column = sa.Column("when_expression", JSONType)


def upgrade():
    return
    add_column(table_name, column)


def downgrade():
    return
    drop_column(table_name, column.name)
