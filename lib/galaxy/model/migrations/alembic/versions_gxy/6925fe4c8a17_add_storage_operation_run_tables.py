"""add storage operation run tables

Revision ID: 6925fe4c8a17
Revises: b75f0f4dbcd4
Create Date: 2026-04-15 16:04:34.330085

"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from galaxy.model.custom_types import (
    JSONType,
    UUIDType,
)
from galaxy.model.migrations.util import (
    create_table,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "6925fe4c8a17"
down_revision = "b75f0f4dbcd4"
branch_labels = None
depends_on = None


def upgrade():
    create_table(
        "dataset_storage_operation_snapshot",
        Column("id", Integer, primary_key=True),
        Column("history_id", Integer, ForeignKey("history.id", ondelete="CASCADE"), index=True),
        Column("user_id", Integer, ForeignKey("galaxy_user.id", ondelete="CASCADE"), index=True, nullable=False),
        Column("mode", String(32), index=True, nullable=False),
        Column("target_object_store_id", String(255), nullable=False),
        Column("resolved_dataset_ids", JSONType, nullable=False),
        Column("eligible_dataset_ids", JSONType, nullable=False),
        Column("create_time", DateTime, nullable=True),
        Column("update_time", DateTime, nullable=True),
        Column("expires_at", DateTime, index=True, nullable=False),
    )

    create_table(
        "dataset_storage_operation_run",
        Column("id", Integer, primary_key=True),
        Column(
            "snapshot_id",
            Integer,
            ForeignKey("dataset_storage_operation_snapshot.id", ondelete="CASCADE"),
            index=True,
        ),
        Column("history_id", Integer, ForeignKey("history.id", ondelete="CASCADE"), index=True),
        Column("user_id", Integer, ForeignKey("galaxy_user.id", ondelete="CASCADE"), index=True, nullable=False),
        Column("mode", String(32), index=True, nullable=False),
        Column("target_object_store_id", String(255), nullable=False),
        Column("state", String(32), index=True, nullable=False),
        Column("skip_ineligible", Boolean, nullable=False, default=True),
        Column("notify_on_completion", Boolean, nullable=False, default=True),
        Column("task_id", UUIDType(), index=True),
        Column("total_count", Integer, nullable=False, default=0),
        Column("succeeded_count", Integer, nullable=False, default=0),
        Column("failed_count", Integer, nullable=False, default=0),
        Column("skipped_count", Integer, nullable=False, default=0),
        Column("total_bytes_processed", Integer, nullable=False, default=0),
        Column("create_time", DateTime, nullable=True),
        Column("update_time", DateTime, nullable=True),
    )

    create_table(
        "dataset_storage_operation_run_item",
        Column("id", Integer, primary_key=True),
        Column("run_id", Integer, ForeignKey("dataset_storage_operation_run.id", ondelete="CASCADE"), index=True),
        Column("dataset_id", Integer, ForeignKey("dataset.id", ondelete="CASCADE"), index=True),
        Column("state", String(32), index=True, nullable=False),
        Column("reason_code", String(64), nullable=True),
        Column("bytes_processed", Integer, nullable=False, default=0),
        Column("create_time", DateTime, nullable=True),
        Column("update_time", DateTime, nullable=True),
        UniqueConstraint("run_id", "dataset_id"),
    )


def downgrade():
    drop_table("dataset_storage_operation_run_item")
    drop_table("dataset_storage_operation_run")
    drop_table("dataset_storage_operation_snapshot")
