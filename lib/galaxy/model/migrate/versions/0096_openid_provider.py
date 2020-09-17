"""
Migration script to add column to openid table for provider.
Remove any OpenID entries with nonunique GenomeSpace Identifier
"""

import logging

from sqlalchemy import Column, MetaData, Table

from galaxy.model.custom_types import TrimmedString

log = logging.getLogger(__name__)
BAD_IDENTIFIER = 'https://identity.genomespace.org/identityServer/xrd.jsp'
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    try:
        OpenID_table = Table("galaxy_user_openid", metadata, autoload=True)
        c = Column("provider", TrimmedString(255))
        c.create(OpenID_table)
        assert c is OpenID_table.c.provider
    except Exception:
        log.exception("Adding provider column to galaxy_user_openid table failed.")

    try:
        cmd = "DELETE FROM galaxy_user_openid WHERE openid='%s'" % (BAD_IDENTIFIER)
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Deleting bad Identifiers from galaxy_user_openid failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        OpenID_table = Table("galaxy_user_openid", metadata, autoload=True)
        OpenID_table.c.provider.drop()
    except Exception:
        log.exception("Dropping provider column from galaxy_user_openid table failed.")
