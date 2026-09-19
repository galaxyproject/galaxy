"""add workflow_comment table

Revision ID: ddbdbc40bdc1
Revises: 92fb564c7095
Create Date: 2023-08-14 13:41:59.442243
"""

import sqlalchemy as sa

from galaxy.model.custom_types import (
    JSONType,
    MutableJSONType,
)
from galaxy.model.migrations.util import (
    add_column,
    create_foreign_key,
    create_table,
    drop_column,
    drop_table,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "ddbdbc40bdc1"
down_revision = "92fb564c7095"
branch_labels = None
depends_on = None

WORKFLOW_COMMENT_TABLE_NAME = "workflow_comment"
WORKFLOW_STEP_TABLE_NAME = "workflow_step"
PARENT_COMMENT_COLUMN_NAME = "parent_comment_id"


def upgrade():
    with transaction():
        create_table(
            WORKFLOW_COMMENT_TABLE_NAME,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("order_index", sa.Integer),
            sa.Column("workflow_id", sa.Integer, sa.ForeignKey("workflow.id")),
            sa.Column("position", MutableJSONType),
            sa.Column("size", JSONType),
            sa.Column("type", sa.String(16)),
            sa.Column("color", sa.String(16)),
            sa.Column("data", JSONType),
            sa.Column(PARENT_COMMENT_COLUMN_NAME, sa.Integer, sa.ForeignKey("workflow_comment.id"), nullable=True),
        )

        add_column(WORKFLOW_STEP_TABLE_NAME, sa.Column(PARENT_COMMENT_COLUMN_NAME, sa.Integer, nullable=True))

        create_foreign_key(
            "foreign_key_parent_comment_id",
            WORKFLOW_STEP_TABLE_NAME,
            WORKFLOW_COMMENT_TABLE_NAME,
            [PARENT_COMMENT_COLUMN_NAME],
            ["id"],
        )


def downgrade():
    with transaction():
        drop_column(WORKFLOW_STEP_TABLE_NAME, PARENT_COMMENT_COLUMN_NAME)
        drop_table(WORKFLOW_COMMENT_TABLE_NAME)
