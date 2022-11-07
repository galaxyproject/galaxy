"""Create default datasetset table and relationships

Revision ID: d7bba32afd32
Revises: b182f655505f
Create Date: 2022-03-27 11:42:44.190610

"""
from alembic import op
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    TEXT,
)

from galaxy.model.custom_types import (
    JSONType,
    TrimmedString,
)
from galaxy.model.orm.now import now

# revision identifiers, used by Alembic.
revision = "d7bba32afd32"
down_revision = "b182f655505f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "default_dataset_association",
        Column("id", Integer, primary_key=True),
        Column("dataset_id", Integer, ForeignKey("dataset.id"), index=True),
        Column("workflow_id", Integer, ForeignKey("workflow.id"), index=True),
        Column("create_time", DateTime, default=now),
        Column("update_time", DateTime, default=now, onupdate=now, index=True),
        Column("state", TrimmedString(64), index=True, key="_state"),
        Column(
            "copied_from_history_dataset_association_id",
            Integer,
            ForeignKey("history_dataset_association.id"),
            nullable=True,
        ),
        Column(
            "copied_from_library_dataset_dataset_association_id",
            Integer,
            ForeignKey("library_dataset_dataset_association.id"),
            nullable=True,
        ),
        Column("name", TrimmedString(255)),
        Column("info", TrimmedString(255)),
        Column("blurb", TrimmedString(255)),
        Column("peek", TEXT, key="_peek"),
        Column("extension", TrimmedString(64)),
        Column("metadata", JSONType, key="_metadata"),
        Column("deleted", Boolean, index=True, default=False),
        Column("extended_metadata_id", Integer, ForeignKey("extended_metadata.id"), index=True),
        Column("purged", Boolean, index=True, default=False),
        Column("validated_state", TrimmedString(64), default="unvalidated", nullable=False),
        Column("validated_state_message", TEXT),
    )
    op.create_table(
        "workflow_step_input_default_dataset_association",
        Column("id", Integer, primary_key=True),
        Column("workflow_step_input_id", Integer, ForeignKey("workflow_step_input.id"), index=True),
        Column("default_dataset_association_id", Integer, ForeignKey("default_dataset_association.id"), index=True),
        Column("name", TEXT),
    )
    op.add_column(
        "workflow_invocation_output_dataset_association",
        Column("default_dataset_id", Integer, ForeignKey("default_dataset_association.id"), index=True, nullable=True),
    )
    op.add_column(
        "workflow_invocation_step_output_dataset_association",
        Column("default_dataset_id", Integer, ForeignKey("default_dataset_association.id"), index=True, nullable=True),
    )


def downgrade():
    op.drop_column("workflow_invocation_output_dataset_association", "default_dataset_id")
    op.drop_column("workflow_invocation_step_output_dataset_association", "default_dataset_id")
    op.drop_table("workflow_step_input_default_dataset_association")
    op.drop_table("default_dataset_association")
