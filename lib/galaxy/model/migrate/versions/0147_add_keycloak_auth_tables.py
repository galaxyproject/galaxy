"""
Migration for keycloak_auth_request.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, MetaData, String, Table

log = logging.getLogger(__name__)
metadata = MetaData()

KeycloakAuthRequest_table = Table(
    "keycloak_auth_request", metadata,
    Column('nonce', String(255), primary_key=True),
    Column('state', String(64))
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        KeycloakAuthRequest_table.create()
    except Exception:
        log.exception("Failed to create {} table".format(KeycloakAuthRequest_table.name))


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        KeycloakAuthRequest_table.drop()
    except Exception:
        log.exception("Failed to drop {} table".format(KeycloakAuthRequest_table.name))
