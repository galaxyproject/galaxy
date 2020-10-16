"""
Migration script to add a new tables for CloudAuthz (tokens required to access cloud-based resources).
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, String, Table, TEXT

from galaxy.model.custom_types import JSONType

log = logging.getLogger(__name__)
metadata = MetaData()

cloudauthz = Table(
    "cloudauthz", metadata,
    Column('id', Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
    Column('provider', String(255)),
    Column('config', JSONType),
    Column('authn_id', Integer, ForeignKey("oidc_user_authnz_tokens.id"), index=True),
    Column('tokens', JSONType),
    Column('last_update', DateTime),
    Column('last_activity', DateTime),
    Column('description', TEXT))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        cloudauthz.create()
    except Exception:
        log.exception("Failed to create cloudauthz table")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        cloudauthz.drop()
    except Exception:
        log.exception("Failed to drop cloudauthz table")
