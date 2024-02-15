"""create celery_user_rate_limit_table

Revision ID: 987ce9839ecb
Revises: b855b714e8b8
Create Date: 2023-05-17 15:08:28.467938

"""

import sqlalchemy as sa

from galaxy.model.migrations.util import (
    create_table,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "987ce9839ecb"
down_revision = "e0561d5fc8c7"
branch_labels = None
depends_on = None


def upgrade():
    create_table(
        "celery_user_rate_limit",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("galaxy_user.id"), primary_key=True),
        sa.Column("last_scheduled_time", sa.DateTime, nullable=False),
    )


def downgrade():
    drop_table("celery_user_rate_limit")
