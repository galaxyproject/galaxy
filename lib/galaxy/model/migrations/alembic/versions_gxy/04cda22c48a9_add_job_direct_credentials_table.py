"""add job_direct_credentials table

Revision ID: 04cda22c48a9
Revises: 9930b68c85af
Create Date: 2026-01-29 15:51:34.502885

"""

import sqlalchemy as sa

from galaxy.model.custom_types import JSONType
from galaxy.model.migrations.util import (
    create_table,
    drop_table,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "04cda22c48a9"
down_revision = "9930b68c85af"
branch_labels = None
depends_on = None


job_direct_credentials_table = "job_direct_credentials"


def upgrade():
    with transaction():
        create_table(
            job_direct_credentials_table,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("job_id", sa.Integer, sa.ForeignKey("job.id"), index=True),
            sa.Column("service_name", sa.String(255)),
            sa.Column("variables", JSONType, nullable=True),
            sa.Column("secrets", JSONType, nullable=True),
        )


def downgrade():
    with transaction():
        drop_table(job_direct_credentials_table)
