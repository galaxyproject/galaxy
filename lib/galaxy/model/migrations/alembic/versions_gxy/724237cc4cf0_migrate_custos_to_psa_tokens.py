"""migrate custos to psa tokens

Revision ID: 724237cc4cf0
Revises: a5c5455b849a
Create Date: 2025-11-03 15:22:13.111461

"""

import json
from datetime import datetime

from alembic import op
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    select,
    String,
    Table,
    Text,
    VARCHAR,
)
from sqlalchemy.orm import Session

from galaxy.model.custom_types import MutableJSONType
from galaxy.model.migrations.util import (
    transaction,
)

# revision identifiers, used by Alembic.
revision = "724237cc4cf0"
down_revision = "a5c5455b849a"
branch_labels = None
depends_on = None

# Table names
CUSTOS_TABLE = "custos_authnz_token"
PSA_TABLE = "oidc_user_authnz_tokens"


def get_custos_table(connection):
    """
    Get the custos_authnz_token Table object for migration operations.

    This function can be reused by both migration scripts and tests.
    """
    return Table(
        CUSTOS_TABLE,
        (
            op.get_bind().dialect.get_columns(op.get_bind(), CUSTOS_TABLE)
            if hasattr(op.get_bind().dialect, "get_columns")
            else []
        ),
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer),
        Column("external_user_id", String(255)),
        Column("provider", String(255)),
        Column("access_token", Text),
        Column("id_token", Text),
        Column("refresh_token", Text),
        Column("expiration_time", DateTime),
        Column("refresh_expiration_time", DateTime),
        extend_existing=True,
        autoload_with=connection,
    )


def get_psa_table(connection):
    """
    Get the oidc_user_authnz_tokens Table object for migration operations.

    This function can be reused by both migration scripts and tests.
    """
    return Table(
        PSA_TABLE,
        (
            op.get_bind().dialect.get_columns(op.get_bind(), PSA_TABLE)
            if hasattr(op.get_bind().dialect, "get_columns")
            else []
        ),
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, ForeignKey("galaxy_user.id")),
        Column("uid", VARCHAR(255)),
        Column("provider", VARCHAR(32)),
        Column("extra_data", MutableJSONType),
        Column("lifetime", Integer),
        Column("assoc_type", VARCHAR(64)),
        extend_existing=True,
        autoload_with=connection,
    )


def migrate_custos_tokens_to_psa(connection, custos_table, psa_table):
    """
    Core migration logic to transform custos tokens to PSA format.

    This function can be reused by both the Alembic migration script and tests.

    Args:
        connection: SQLAlchemy database connection
        custos_table: SQLAlchemy Table object for custos_authnz_token
        psa_table: SQLAlchemy Table object for oidc_user_authnz_tokens

    Returns:
        int: Number of tokens migrated
    """
    # Read all custos tokens
    custos_records = connection.execute(select(custos_table)).fetchall()

    migrated_count = 0
    for record in custos_records:
        # Check if this token has already been migrated
        existing = connection.execute(
            select(psa_table).where(
                psa_table.c.user_id == record.user_id,
                psa_table.c.provider == record.provider,
                psa_table.c.uid == record.external_user_id,
            )
        ).first()

        if existing:
            # Already migrated, skip
            continue

        # Build extra_data JSON structure compatible with PSA
        extra_data = {}

        if record.access_token:
            extra_data["access_token"] = record.access_token

        if record.id_token:
            extra_data["id_token"] = record.id_token

        if record.refresh_token:
            extra_data["refresh_token"] = record.refresh_token

        # Calculate auth_time and expires for PSA compatibility
        if record.expiration_time:
            now = datetime.now()
            auth_time = int(now.timestamp())
            expires_at = int(record.expiration_time.timestamp())
            expires = expires_at - auth_time

            extra_data["auth_time"] = auth_time
            extra_data["expires"] = expires if expires > 0 else 3600  # Default to 1 hour if negative

        # For refresh token expiration
        if record.refresh_expiration_time:
            refresh_expires_at = int(record.refresh_expiration_time.timestamp())
            if "refresh_token" in extra_data:
                extra_data["refresh_expires_in"] = refresh_expires_at - int(datetime.now().timestamp())

        # Insert into PSA table
        connection.execute(
            psa_table.insert().values(
                user_id=record.user_id,
                uid=record.external_user_id,
                provider=record.provider,
                extra_data=extra_data,
                lifetime=None,
                assoc_type=None,
            )
        )
        migrated_count += 1

    return migrated_count


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
        session = Session(bind=connection)

        # Get table definitions
        custos_table = get_custos_table(connection)
        psa_table = get_psa_table(connection)

        # Run the core migration logic
        migrated_count = migrate_custos_tokens_to_psa(connection, custos_table, psa_table)

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

        # Get table definitions
        custos_table = get_custos_table(connection)
        psa_table = get_psa_table(connection)

        # Get all custos records to identify which PSA records to remove
        custos_records = connection.execute(select(custos_table)).fetchall()

        removed_count = 0
        for record in custos_records:
            # Delete corresponding PSA record
            result = connection.execute(
                psa_table.delete().where(
                    psa_table.c.user_id == record.user_id,
                    psa_table.c.provider == record.provider,
                    psa_table.c.uid == record.external_user_id,
                )
            )
            removed_count += result.rowcount

        print(f"Removed {removed_count} migrated tokens from {PSA_TABLE}")
