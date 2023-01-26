"""Add reason column on invocation table

Revision ID: 3100452fa030
Revises: 518c8438a91b
Create Date: 2023-01-13 16:13:09.578391

"""
from alembic import op
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
)

from galaxy.model.custom_types import TrimmedString

# revision identifiers, used by Alembic.
revision = "3100452fa030"
down_revision = "518c8438a91b"
branch_labels = None
depends_on = None


# database object names used in this revision
table_name = "workflow_invocation_message"


def upgrade():
    op.create_table(
        table_name,
        Column("id", Integer, primary_key=True),
        Column("reason", String(32)),
        Column("details", TrimmedString(255)),
        Column("output_name", String(255)),
        Column("workflow_invocation_id", Integer, ForeignKey("workflow_invocation.id"), index=True, nullable=False),
        Column("workflow_step_id", Integer, ForeignKey("workflow_step.id"), nullable=True),
        Column("dependent_workflow_step_id", Integer, ForeignKey("workflow_step.id"), nullable=True),
        Column("job_id", Integer, ForeignKey("job.id"), nullable=True),
        Column("hda_id", Integer, ForeignKey("history_dataset_association.id"), nullable=True),
        Column("hdca_id", Integer, ForeignKey("history_dataset_collection_association.id"), nullable=True),
    )


def downgrade():
    op.drop_table(table_name)
