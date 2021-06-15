"""
Migration for adding custos_authnz_token table.
"""

import logging

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint
)

from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)

log = logging.getLogger(__name__)
metadata = MetaData()

CustosAuthnzToken_table = Table(
    "custos_authnz_token", metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey("galaxy_user.id")),
    Column('external_user_id', String(64)),
    Column('provider', String(255)),
    Column('access_token', Text),
    Column('id_token', Text),
    Column('refresh_token', Text),
    Column("expiration_time", DateTime),
    Column("refresh_expiration_time", DateTime),
    UniqueConstraint("user_id", "external_user_id", "provider"),
    UniqueConstraint("external_user_id", "provider"),
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(CustosAuthnzToken_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(CustosAuthnzToken_table)
