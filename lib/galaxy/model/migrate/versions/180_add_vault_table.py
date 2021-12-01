import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Table, Text

now = datetime.datetime.utcnow
meta = MetaData()

vault = Table(
    'vault', meta,
    Column('id', Integer, primary_key=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    Column('key', Text, index=True, unique=True),
    Column('value', Text, nullable=True),
    Column('parent_key', Text, ForeignKey('vault.key'), index=True, nullable=True)
)


def upgrade(migrate_engine):
    meta.bind = migrate_engine
    vault.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    vault.drop()
