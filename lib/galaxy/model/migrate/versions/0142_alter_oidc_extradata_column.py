"""
Migration script to alter the type of `extra_data` column of `oidc_user_authnz_tokens` table from TEXT to JSON.
"""
from __future__ import print_function

import logging

from galaxy.model.custom_types import JSONType
from sqlalchemy import MetaData, Table, TEXT

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        table = Table("oidc_user_authnz_tokens", metadata, autoload=True)
        table.c.extra_data.alter(type=JSONType, nullable=True)
    except Exception as e:
        log.exception("Altering the `extra_data` column type from TEXT to JSON failed: %s" % str(e))


def downgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        table = Table("oidc_user_authnz_tokens", metadata, autoload=True)
        table.c.extra_data.alter(type=TEXT)
    except Exception as e:
        log.exception("Altering the `extra_data` column type from JSON to TEXT failed: %s" % str(e))
