"""add dataset_protection_grant table and job.protection_scheme column

Revision ID: 83bb43259ae6
Revises: 64d49ad328d4
Create Date: 2026-10-05 12:00:00.000000

"""

import sqlalchemy as sa

from galaxy.model.custom_types import JSONType
from galaxy.model.migrations.util import (
    add_column,
    create_table,
    drop_column,
    drop_table,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "83bb43259ae6"
down_revision = "64d49ad328d4"
branch_labels = None
depends_on = None

# database object names used in this revision
grant_table_name = "dataset_protection_grant"
job_table_name = "job"
job_column_name = "protection_scheme"


def upgrade() -> None:
    with transaction():
        create_table(
            grant_table_name,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("galaxy_user.id"), index=True, nullable=False),
            sa.Column("dataset_id", sa.Integer, sa.ForeignKey("dataset.id"), index=True, nullable=False),
            sa.Column("scheme", sa.String(32), nullable=False),
            sa.Column("key_ref", sa.String(255), nullable=False),
            sa.Column("expires_at", sa.DateTime, nullable=False),
            sa.Column("grant_data", JSONType, nullable=False),
            sa.Column("source", sa.String(64), nullable=False),
            sa.Column("create_time", sa.DateTime, nullable=False),
            sa.Column("update_time", sa.DateTime, nullable=False),
            sa.UniqueConstraint("user_id", "dataset_id", "scheme"),
        )
        add_column(job_table_name, sa.Column(job_column_name, sa.String(32), nullable=True))


def downgrade() -> None:
    with transaction():
        drop_column(job_table_name, job_column_name)
        drop_table(grant_table_name)
