"""Add id_key column to oidc_user_authnz_tokens

social-auth-core 6 records which response field (``id_key``) each association's
``uid`` was taken from. Existing associations are backfilled with the key their
backend used before social-auth-core 6.0, so that social-auth-core can find them
and, for backends whose default key has changed (e.g. Google from ``email`` to
``sub``), migrate them on the user's next login.

Revision ID: ddd0f036e070
Revises: b9467a8c12de
Create Date: 2026-11-19 11:58:19.823758

"""

import sqlalchemy as sa
from alembic import op

from galaxy.model.migrations.util import (
    add_column,
    drop_column,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "ddd0f036e070"
down_revision = "b9467a8c12de"
branch_labels = None
depends_on = None

table_name = "oidc_user_authnz_tokens"
column_name = "id_key"

# Identifier keys used by Galaxy's backends (``galaxy.authnz.psa_authnz.BACKENDS``)
# with social-auth-core 5.2.0, frozen so that the migration doesn't depend on the
# installed social-auth-core version. Tapis builds the uid itself, but
# social-auth-core reports the ``BaseOAuth2`` default key.
# Google is handled separately below.
OLD_ID_KEYS = {
    "auth0": "sub",
    "azuread-v2-tenant-oauth2": "preferred_username",
    "cilogon": "sub",
    "e-infra_cz": "sub",
    "egi-checkin": "sub",
    "elixir": "sub",
    "globus": "sub",
    "helmholtz": "sub",
    "infraproxy": "sub",
    "keycloak": "sub",
    "life_science": "sub",
    "oidc": "sub",
    "okta-openidconnect": "preferred_username",
    "tapis": "id",
}


def upgrade() -> None:
    with transaction():
        add_column(table_name, sa.Column(column_name, sa.String(255), nullable=False, server_default=""))
        table = sa.sql.table(
            table_name,
            sa.Column("provider", sa.String(32)),
            sa.Column("uid", sa.String(255)),
            sa.Column(column_name, sa.String(255)),
        )
        for provider, id_key in OLD_ID_KEYS.items():
            op.execute(table.update().where(table.c.provider == provider, table.c.id_key == "").values(id_key=id_key))
        # Google used the email as uid, unless ``GOOGLE_OPENIDCONNECT_USE_UNIQUE_USER_ID``
        # was set, in which case it used ``sub``. Tell them apart by the uid itself.
        google = table.c.provider == "google-openidconnect"
        op.execute(table.update().where(google, table.c.id_key == "", table.c.uid.like("%@%")).values(id_key="email"))
        op.execute(table.update().where(google, table.c.id_key == "").values(id_key="sub"))


def downgrade() -> None:
    with transaction():
        drop_column(table_name, column_name)
