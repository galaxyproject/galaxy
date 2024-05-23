"""drop cloudauthz table

Revision ID: 570bce1e82f9
Revises: c14a3c93d66b
Create Date: 2024-05-21 15:53:06.430082

"""

import sqlalchemy as sa

from galaxy.model.custom_types import MutableJSONType
from galaxy.model.migrations.util import (
    create_table,
    drop_table,
    transaction,
)
from galaxy.model.orm.now import now

# revision identifiers, used by Alembic.
revision = "570bce1e82f9"
down_revision = "c14a3c93d66b"
branch_labels = None
depends_on = None

CLOUDAUTHZ_TABLE_NAME = "cloudauthz"


def upgrade():
    with transaction():
        drop_table(CLOUDAUTHZ_TABLE_NAME)


def downgrade():
    with transaction():
        create_table(
            CLOUDAUTHZ_TABLE_NAME,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("galaxy_user.id"), index=True),
            sa.Column("provider", sa.String(255)),
            sa.Column("config", MutableJSONType),
            sa.Column("authn_id", sa.Integer, sa.ForeignKey("oidc_user_authnz_tokens.id"), index=True),
            sa.Column("tokens", MutableJSONType),
            sa.Column("last_update", sa.DateTime),
            sa.Column("last_activity", sa.DateTime),
            sa.Column("description", sa.Text),
            sa.Column("create_time", sa.DateTime, default=now),
        )
