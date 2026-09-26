"""create celery_user_active_task table

Revision ID: f5e9e4bca542
Revises: 566b691307a5
Create Date: 2026-03-19 10:00:00.000000

"""

import sqlalchemy as sa

from galaxy.model.migrations.util import (
    create_table,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "f5e9e4bca542"
down_revision = "566b691307a5"
branch_labels = None
depends_on = None


def upgrade():
    create_table(
        "celery_user_active_task",
        sa.Column("task_id", sa.String(255), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("galaxy_user.id", ondelete="CASCADE"), index=True),
        sa.Column("started_at", sa.DateTime, nullable=False),
    )


def downgrade():
    drop_table("celery_user_active_task")
