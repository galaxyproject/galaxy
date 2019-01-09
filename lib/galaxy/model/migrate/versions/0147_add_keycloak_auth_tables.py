"""
Migration for adding keycloak_access_token table.
"""
from __future__ import print_function

import logging

from sqlalchemy import (Column, DateTime, ForeignKey, Integer, MetaData,
                        String, Table, Text)

from galaxy.model.custom_types import JSONType

log = logging.getLogger(__name__)
metadata = MetaData()

KeycloakAccessToken_table = Table(
    "keycloak_access_token", metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey("galaxy_user.id"), unique=True, index=True),
    Column('keycloak_user_id', String(64), unique=True, index=True),
    Column('access_token', Text),
    Column('id_token', Text),
    Column('refresh_token', Text),
    Column("expiration_time", DateTime),
    Column("refresh_expiration_time", DateTime),
    Column('raw_token', JSONType, nullable=True),
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        KeycloakAccessToken_table.create()
    except Exception:
        log.exception("Failed to create Keycloak auth tables")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        KeycloakAccessToken_table.drop()
    except Exception:
        log.exception("Failed to drop Keycloak auth tables")
