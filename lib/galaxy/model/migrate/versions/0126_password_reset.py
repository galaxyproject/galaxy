"""
Migration script for the password reset table
"""

import logging

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, String, Table

from galaxy.model.migrate.versions.util import create_table, drop_table

log = logging.getLogger(__name__)
metadata = MetaData()

PasswordResetToken_table = Table("password_reset_token", metadata,
                                 Column("token", String(32), primary_key=True, unique=True, index=True),
                                 Column("expiration_time", DateTime),
                                 Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(PasswordResetToken_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(PasswordResetToken_table)
