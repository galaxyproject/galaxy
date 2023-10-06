"""add orcid id to galaxy_user

Revision ID: de41c9131a19
Revises: 987ce9839ecb
Create Date: 2023-10-06 11:48:17.216554

"""
import sqlalchemy as sa

from galaxy.model.migrations.util import (
    add_column,
    drop_column,
    transaction,
)

# revision identifiers, used by Alembic.
revision = 'de41c9131a19'
down_revision = '987ce9839ecb'
branch_labels = None
depends_on = None

table_name = "galaxy_user"

orcid_id_column_name = "orcid_id"


def upgrade():
    with transaction():
        _add_column_orcid_id()


def downgrade():
    with transaction():
        _drop_column_orcid_id()


def _add_column_orcid_id():
    add_column(
        table_name,
        sa.Column(orcid_id_column_name, sa.String, nullable=True, default=None),
    )


def _drop_column_orcid_id():
    drop_column(table_name, orcid_id_column_name)
