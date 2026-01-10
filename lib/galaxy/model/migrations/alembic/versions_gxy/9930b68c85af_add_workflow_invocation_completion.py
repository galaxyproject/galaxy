"""add workflow_invocation_completion table and on_complete column

Revision ID: 9930b68c85af
Revises: 312602e3191d
Create Date: 2026-01-03 12:00:00.000000

"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
)

from galaxy.model.migrations.util import (
    add_column,
    create_table,
    drop_column,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "9930b68c85af"
down_revision = "312602e3191d"
branch_labels = None
depends_on = None


table_name = "workflow_invocation_completion"


def upgrade():
    create_table(
        table_name,
        Column("id", Integer, primary_key=True),
        Column(
            "workflow_invocation_id",
            Integer,
            ForeignKey("workflow_invocation.id"),
            index=True,
            unique=True,
            nullable=False,
        ),
        Column("completion_time", DateTime),
        Column("job_state_summary", JSON),
        Column("all_jobs_ok", Boolean, default=False),
        Column("hooks_executed", JSON),
    )
    # Add column to workflow_invocation for per-invocation completion actions
    add_column(
        "workflow_invocation",
        Column("on_complete", JSON),
    )


def downgrade():
    drop_column("workflow_invocation", "on_complete")
    drop_table(table_name)
