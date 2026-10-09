"""create admin_setting table

Revision ID: b7c1d2e3f4a5
Revises: a4c3f2e1b790
Create Date: 2026-09-27 10:00:00.000000

"""

import sqlalchemy as sa

from galaxy.model.custom_types import MutableJSONType
from galaxy.model.migrations.util import (
    create_table,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "b7c1d2e3f4a5"
down_revision = "64d49ad328d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table(
        "admin_setting",
        sa.Column("key", sa.String(255), primary_key=True),
        sa.Column("value", MutableJSONType),
        sa.Column("create_time", sa.DateTime),
        sa.Column("update_time", sa.DateTime),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("galaxy_user.id", ondelete="SET NULL"), index=True),
    )


def downgrade() -> None:
    drop_table("admin_setting")
