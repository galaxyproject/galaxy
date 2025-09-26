"""Create landing request association tables

Revision ID: e382f8eb5e12
Revises: 81362686fd64
Create Date: 2025-09-26 12:39:25.000000

"""

import sqlalchemy as sa

from galaxy.model.migrations.util import (
    create_table,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "e382f8eb5e12"
down_revision = "81362686fd64"
branch_labels = None
depends_on = None

# database object names used in this revision
workflow_association_table = "landing_request_to_workflow_invocation_association"
tool_association_table = "landing_request_to_tool_request_association"


def upgrade():
    # Create landing_request_to_workflow_invocation_association table
    create_table(
        workflow_association_table,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("landing_request_id", sa.Integer, sa.ForeignKey("workflow_landing_request.id"), nullable=False),
        sa.Column("workflow_invocation_id", sa.Integer, sa.ForeignKey("workflow_invocation.id"), nullable=False),
    )

    # Create landing_request_to_tool_request_association table
    create_table(
        tool_association_table,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("landing_request_id", sa.Integer, sa.ForeignKey("tool_landing_request.id"), nullable=False),
        sa.Column("tool_request_id", sa.Integer, sa.ForeignKey("tool_request.id"), nullable=False),
    )


def downgrade():
    # Drop both association tables
    drop_table(workflow_association_table)
    drop_table(tool_association_table)
