"""create page_embed_token table

Revision ID: f0e1d2c3b4a5
Revises: 28885b317f78
Create Date: 2026-06-20 12:00:00.000000

"""

import sqlalchemy as sa

from galaxy.model.migrations.util import (
    create_table,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "f0e1d2c3b4a5"
down_revision = "28885b317f78"
branch_labels = None
depends_on = None


def upgrade():
    create_table(
        "page_embed_token",
        sa.Column("token", sa.String(32), primary_key=True),
        sa.Column("page_id", sa.Integer, sa.ForeignKey("page.id", ondelete="CASCADE"), index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("galaxy_user.id", ondelete="CASCADE"), index=True),
        sa.Column("expiration_time", sa.DateTime, nullable=False),
    )


def downgrade():
    drop_table("page_embed_token")
