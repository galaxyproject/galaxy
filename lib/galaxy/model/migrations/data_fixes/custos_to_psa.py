"""Reusable helpers for migrating Custos authentication tokens into PSA format."""

import jwt
from datetime import datetime
from typing import (
    cast,
    Optional,
)

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    select,
    String,
    Table,
    Text,
)
from sqlalchemy.engine import Connection

from galaxy.model import UserAuthnzToken

CUSTOS_TABLE = "custos_authnz_token"
PSA_TABLE = "oidc_user_authnz_tokens"
CUSTOS_ASSOC_TYPE = "custos_migrated"


def _extract_iat_from_token(token: str) -> Optional[int]:
    """
    Extract the 'iat' (issued at) claim from a JWT token.
    Returns None if the token cannot be decoded or doesn't have an iat claim.
    """
    if not token:
        return None
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded.get("iat")
    except Exception:
        return None


def get_custos_table(connection: Connection) -> Table:
    """
    Reflect the custos_authnz_token table for use in migrations or tests.
    """
    return Table(
        CUSTOS_TABLE,
        MetaData(),
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


def get_psa_table(connection: Connection) -> Table:
    """
    Get the oidc_user_authnz_tokens table directly from the UserAuthnzToken model.
    """
    return cast(Table, UserAuthnzToken.table)


def migrate_custos_tokens_to_psa(
    connection: Connection,
    custos_table: Optional[Table] = None,
    psa_table: Optional[Table] = None,
) -> int:
    """
    Transform Custos tokens into PSA tokens and insert them into oidc_user_authnz_tokens.

    :returns: Number of tokens that were migrated.
    """
    if custos_table is None:
        custos_table = get_custos_table(connection)
    if psa_table is None:
        psa_table = get_psa_table(connection)

    custos_records = connection.execute(select(custos_table)).fetchall()

    migrated_count = 0
    for record in custos_records:
        now_ts = int(datetime.now().timestamp())
        existing = connection.execute(
            select(psa_table).where(
                psa_table.c.user_id == record.user_id,
                psa_table.c.provider == record.provider,
                psa_table.c.uid == record.external_user_id,
            )
        ).first()

        if existing:
            continue

        extra_data = {}
        if record.access_token:
            extra_data["access_token"] = record.access_token
        if record.id_token:
            extra_data["id_token"] = record.id_token
        if record.refresh_token:
            extra_data["refresh_token"] = record.refresh_token

        # Extract auth_time from token's 'iat' claim (issued at time)
        # Priority: access_token.iat > id_token.iat > current time
        # We prefer access_token.iat since that's the token whose expiration we're tracking
        auth_time = (
            _extract_iat_from_token(record.access_token)
            or _extract_iat_from_token(record.id_token)
            or now_ts
        )
        extra_data["auth_time"] = auth_time

        # Calculate expires from expiration_time
        # If token is expired or expiration_time is missing, set expires to 1 second
        # to trigger immediate refresh on next use
        if record.expiration_time:
            expires_at = int(record.expiration_time.timestamp())
            # Check if token is already expired (expiration_time < now)
            if expires_at <= now_ts:
                # Token already expired - set to 1 second to trigger refresh
                extra_data["expires"] = 1
            else:
                # Token still valid - calculate original lifetime
                expires = expires_at - auth_time
                extra_data["expires"] = expires if expires > 0 else 1
        else:
            # No expiration_time - set to 1 second to trigger refresh
            extra_data["expires"] = 1

        if record.refresh_expiration_time and "refresh_token" in extra_data:
            refresh_expires_at = int(record.refresh_expiration_time.timestamp())
            extra_data["refresh_expires_in"] = refresh_expires_at - now_ts

        connection.execute(
            psa_table.insert().values(
                user_id=record.user_id,
                uid=record.external_user_id,
                provider=record.provider,
                extra_data=extra_data,
                lifetime=None,
                assoc_type=CUSTOS_ASSOC_TYPE,
            )
        )
        migrated_count += 1

    return migrated_count


def remove_migrated_psa_tokens(
    connection: Connection,
    custos_table: Optional[Table] = None,
    psa_table: Optional[Table] = None,
) -> int:
    """
    Remove PSA tokens that were created during the Custos migration.

    :returns: Number of PSA rows removed.
    """
    if custos_table is None:
        custos_table = get_custos_table(connection)
    if psa_table is None:
        psa_table = get_psa_table(connection)

    custos_records = connection.execute(select(custos_table)).fetchall()

    removed_count = 0
    for record in custos_records:
        result = connection.execute(
            psa_table.delete().where(
                psa_table.c.user_id == record.user_id,
                psa_table.c.provider == record.provider,
                psa_table.c.uid == record.external_user_id,
                psa_table.c.assoc_type == CUSTOS_ASSOC_TYPE,
            )
        )
        removed_count += result.rowcount

    return removed_count


def restore_custos_tokens_from_psa(
    connection: Connection,
    custos_table: Optional[Table] = None,
    psa_table: Optional[Table] = None,
) -> int:
    """
    Restore Custos tokens from PSA rows that originated from the migration.

    :returns: Number of tokens restored into custos_authnz_token.
    """
    if custos_table is None:
        custos_table = get_custos_table(connection)
    if psa_table is None:
        psa_table = get_psa_table(connection)

    psa_records = connection.execute(select(psa_table).where(psa_table.c.assoc_type == CUSTOS_ASSOC_TYPE)).fetchall()

    restored_count = 0
    for record in psa_records:
        extra_data = record.extra_data or {}
        expiration_time = None
        refresh_expiration_time = None

        auth_time = extra_data.get("auth_time")
        expires = extra_data.get("expires")
        refresh_expires_in = extra_data.get("refresh_expires_in")

        if auth_time is not None:
            auth_time = int(auth_time)
        if expires is not None:
            expires = int(expires)
        if refresh_expires_in is not None:
            refresh_expires_in = int(refresh_expires_in)

        if auth_time is not None and expires is not None:
            expiration_time = datetime.fromtimestamp(auth_time + expires)

        if auth_time is not None and refresh_expires_in is not None:
            refresh_expiration_time = datetime.fromtimestamp(auth_time + refresh_expires_in)

        connection.execute(
            custos_table.insert().values(
                user_id=record.user_id,
                external_user_id=record.uid,
                provider=record.provider,
                access_token=extra_data.get("access_token"),
                id_token=extra_data.get("id_token"),
                refresh_token=extra_data.get("refresh_token"),
                expiration_time=expiration_time,
                refresh_expiration_time=refresh_expiration_time,
            )
        )
        restored_count += 1

    return restored_count
