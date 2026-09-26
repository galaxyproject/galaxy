"""add last_login column to galaxy_user

Revision ID: 91c8b337d76b
Revises: 64d49ad328d4
Create Date: 2026-09-26 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "91c8b337d76b"
down_revision = "64d49ad328d4"
branch_labels = None
depends_on = None


table_name = "galaxy_user"
column_name = "last_login"


def upgrade() -> None:
    add_column(table_name, sa.Column(column_name, sa.DateTime, nullable=True))
    op.execute(
        """
        UPDATE galaxy_user
        SET last_login = (
            SELECT max(galaxy_session.update_time)
            FROM galaxy_session
            WHERE galaxy_session.user_id = galaxy_user.id
        )
        WHERE EXISTS (
            SELECT 1
            FROM galaxy_session
            WHERE galaxy_session.user_id = galaxy_user.id
        )
        """
    )


def downgrade() -> None:
    drop_column(table_name, column_name)
