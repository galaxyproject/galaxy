"""migrate custos to psa tokens

Revision ID: 724237cc4cf0
Revises: 1d1d7bf6ac02
Create Date: 2025-11-03 15:22:13.111461

"""

from alembic import op

from galaxy.model.migrations.data_fixes.custos_to_psa import (
    CUSTOS_TABLE,
    migrate_custos_tokens_to_psa,
    PSA_TABLE,
    remove_migrated_psa_tokens,
)
from galaxy.model.migrations.util import transaction

# revision identifiers, used by Alembic.
revision = "724237cc4cf0"
down_revision = "1d1d7bf6ac02"
branch_labels = None
depends_on = None


def upgrade():
    """
    Migrate authentication tokens from custos_authnz_token to oidc_user_authnz_tokens.

    This involves:
    1. Reading all records from custos_authnz_token
    2. Transforming the data structure (separate token fields -> JSON extra_data)
    3. Inserting into oidc_user_authnz_tokens
    4. Keeping custos_authnz_token table for rollback capability
    """
    with transaction():
        connection = op.get_bind()
        migrated_count = migrate_custos_tokens_to_psa(connection)
        print(f"Migrated {migrated_count} tokens from {CUSTOS_TABLE} to {PSA_TABLE}")


def downgrade():
    """
    Rollback the migration by removing migrated tokens from oidc_user_authnz_tokens.

    Note: This only removes tokens that were migrated from custos_authnz_token.
    The custos_authnz_token table is not modified during upgrade, so original
    data is preserved for downgrade.
    """
    with transaction():
        connection = op.get_bind()
        removed_count = remove_migrated_psa_tokens(connection)
        print(f"Removed {removed_count} migrated tokens from {PSA_TABLE}")
