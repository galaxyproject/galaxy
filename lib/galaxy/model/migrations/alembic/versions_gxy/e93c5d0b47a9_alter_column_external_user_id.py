"""alter column CustosAuthnzToken.external_user_id to increase length

Revision ID: e93c5d0b47a9
Revises: e0561d5fc8c7
Create Date: 2023-10-08 12:11:02.024669

"""

import sqlalchemy as sa

from galaxy.model.migrations.util import alter_column

# revision identifiers, used by Alembic.
revision = "e93c5d0b47a9"
down_revision = "e0561d5fc8c7"
branch_labels = None
depends_on = None

table_name = "custos_authnz_token"
column_name = "external_user_id"

LONGER_LENGTH = 255


def upgrade():
    alter_column(table_name, column_name, type_=sa.String(LONGER_LENGTH))


def downgrade():
    # No need to downgrade, this is a one-way migration. Otherwise, existing data would be truncated or lost.
    pass
