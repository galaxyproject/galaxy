"""migrate custos to psa tokens

Revision ID: 724237cc4cf0
Revises: 1d1d7bf6ac02
Create Date: 2025-11-03 15:22:13.111461

"""

import sqlalchemy as sa
from alembic import op

from galaxy.model.migrations.data_fixes.custos_to_psa import (
    CUSTOS_TABLE,
    migrate_custos_tokens_to_psa,
    remove_migrated_psa_tokens,
    restore_custos_tokens_from_psa,
)
from galaxy.model.migrations.util import (
    create_table,
    create_unique_constraint,
    drop_table,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "724237cc4cf0"
down_revision = "1d1d7bf6ac02"
branch_labels = None
depends_on = None

_USER_EXTERNAL_PROVIDER_CONSTRAINT = "custos_authnz_token_user_id_external_user_id_provider_key"
_EXTERNAL_PROVIDER_CONSTRAINT = "custos_authnz_token_external_user_id_provider_key"


def upgrade():
    """
    Migrate authentication tokens from custos_authnz_token to oidc_user_authnz_tokens
    and drop the obsolete custos_authnz_token table.
    """
    with transaction():
        connection = op.get_bind()
        migrate_custos_tokens_to_psa(connection)
        drop_table(CUSTOS_TABLE)


def downgrade():
    """
    Recreate custos_authnz_token and restore any Custos tokens that were migrated.
    """
    with transaction():
        connection = op.get_bind()
        create_table(
            CUSTOS_TABLE,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("galaxy_user.id"), index=True),
            sa.Column("external_user_id", sa.String(255)),
            sa.Column("provider", sa.String(255)),
            sa.Column("access_token", sa.Text),
            sa.Column("id_token", sa.Text),
            sa.Column("refresh_token", sa.Text),
            sa.Column("expiration_time", sa.DateTime),
            sa.Column("refresh_expiration_time", sa.DateTime),
        )
        create_unique_constraint(
            _USER_EXTERNAL_PROVIDER_CONSTRAINT,
            CUSTOS_TABLE,
            ["user_id", "external_user_id", "provider"],
        )
        create_unique_constraint(
            _EXTERNAL_PROVIDER_CONSTRAINT,
            CUSTOS_TABLE,
            ["external_user_id", "provider"],
        )
        restore_custos_tokens_from_psa(connection)
        remove_migrated_psa_tokens(connection)
