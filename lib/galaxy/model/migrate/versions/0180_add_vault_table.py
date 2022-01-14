import datetime

from sqlalchemy import Column, DateTime, ForeignKey, MetaData, Table, Text

now = datetime.datetime.utcnow
meta = MetaData()

vault = Table(
    'vault', meta,
    Column('key', Text, primary_key=True),
    Column('parent_key', Text, ForeignKey('vault.key'), index=True, nullable=True),
    Column('value', Text, nullable=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now)
)


def upgrade(migrate_engine):
    meta.bind = migrate_engine
    vault.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    vault.drop()
