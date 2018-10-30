"""
Migration script to add a new tables for an OpenID Connect authentication and authorization.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, TEXT, VARCHAR

from galaxy.model.custom_types import JSONType

log = logging.getLogger(__name__)
metadata = MetaData()

psa_association = Table(
    "psa_association", metadata,
    Column('id', Integer, primary_key=True),
    Column('server_url', VARCHAR(255)),
    Column('handle', VARCHAR(255)),
    Column('secret', VARCHAR(255)),
    Column('issued', Integer),
    Column('lifetime', Integer),
    Column('assoc_type', VARCHAR(64)))


psa_code = Table(
    "psa_code", metadata,
    Column('id', Integer, primary_key=True),
    Column('email', VARCHAR(200)),
    Column('code', VARCHAR(32)))


psa_nonce = Table(
    "psa_nonce", metadata,
    Column('id', Integer, primary_key=True),
    Column('server_url', VARCHAR(255)),
    Column('timestamp', Integer),
    Column('salt', VARCHAR(40)))


psa_partial = Table(
    "psa_partial", metadata,
    Column('id', Integer, primary_key=True),
    Column('token', VARCHAR(32)),
    Column('data', TEXT),
    Column('next_step', Integer),
    Column('backend', VARCHAR(32)))


oidc_user_authnz_tokens = Table(
    "oidc_user_authnz_tokens", metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey("galaxy_user.id"), index=True),
    Column('uid', VARCHAR(255)),
    Column('provider', VARCHAR(32)),
    Column('extra_data', JSONType, nullable=True),
    Column('lifetime', Integer),
    Column('assoc_type', VARCHAR(64)))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        psa_association.create()
        psa_code.create()
        psa_nonce.create()
        psa_partial.create()
        oidc_user_authnz_tokens.create()
    except Exception:
        log.exception("Creating OIDC table failed")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        psa_association.drop()
        psa_code.drop()
        psa_nonce.drop()
        psa_partial.drop()
        oidc_user_authnz_tokens.drop()
    except Exception:
        log.exception("Dropping OIDC table failed")
