"""Add compute_resource + compute_resource_registration tables

Revision ID: fe9dd3972993
Revises: 6925fe4c8a17
Create Date: 2026-05-11 12:00:00.000000

"""

import sqlalchemy as sa

from galaxy.model.migrations.util import (
    create_table,
    drop_table,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "fe9dd3972993"
down_revision = "6925fe4c8a17"
branch_labels = None
depends_on = None

RESOURCE_TABLE = "compute_resource"
REGISTRATION_TABLE = "compute_resource_registration"


def upgrade():
    """Create the tables backing user-self-registered compute resources.

    The relay refresh token associated with each resource is stored in the Galaxy
    vault, not in these tables. ``compute_resource_registration`` holds short-lived
    single-use tokens that authorise the
    ``POST /api/compute_resources/registrations/complete`` callback from the user's host.

    ``ondelete="CASCADE"`` on the ``user_id`` FKs: deleting a Galaxy user
    removes their compute_resource rows and any unredeemed registration tokens
    along with them, so the vault entries (cleared by
    :meth:`ComputeResourceManager.purge`) aren't orphaned by an admin user delete.
    """
    with transaction():
        create_table(
            RESOURCE_TABLE,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("galaxy_user.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("manager_name", sa.String(96), nullable=False, unique=True),
            sa.Column("relay_url", sa.Text, nullable=False),
            sa.Column("relay_topic_prefix", sa.String(96), nullable=True),
            sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
            sa.Column("create_time", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column(
                "update_time",
                sa.DateTime,
                nullable=False,
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
            sa.Column("last_seen_time", sa.DateTime, nullable=True),
        )
        create_table(
            REGISTRATION_TABLE,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("token", sa.String(64), nullable=False, unique=True, index=True),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("galaxy_user.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("create_time", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column("expiration_time", sa.DateTime, nullable=False),
        )


def downgrade():
    with transaction():
        drop_table(REGISTRATION_TABLE)
        drop_table(RESOURCE_TABLE)
