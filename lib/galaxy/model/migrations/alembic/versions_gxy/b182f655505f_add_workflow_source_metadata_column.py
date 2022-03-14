"""add workflow.source_metadata column

Revision ID: b182f655505f
Revises: e7b6dcb09efd
Create Date: 2022-03-14 12:56:57.067748

"""
from alembic import op
from sqlalchemy import Column

from galaxy.model.custom_types import JSONType

# revision identifiers, used by Alembic.
revision = "b182f655505f"
down_revision = "e7b6dcb09efd"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("workflow", Column("source_metadata", JSONType))


def downgrade():
    with op.batch_alter_table("workflow") as batch_op:
        batch_op.drop_column("source_metadata")
