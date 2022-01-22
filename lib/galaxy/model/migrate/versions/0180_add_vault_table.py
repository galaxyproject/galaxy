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
    # This revision is not part of 21.09, but in 22.01 it will be handled by Alembic.
    # It is possible to reach a state (via upgrading/downgrading) where this table
    # will have been dropped by Alembic, but SQLAlchemy Migrate (our previous
    # db migrations tool) will have version 180 (which includes this table).
    # Downgrading from such a state would raise an error - which this code prevents.
    try:
        vault.drop()
    except Exception:
        pass
