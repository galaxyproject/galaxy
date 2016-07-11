"""
Migration script to add a last_password_change field to the user table
"""

from sqlalchemy import Table, MetaData, DateTime, Column


def upgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)
    account = Table('galaxy_user', meta, autoload=True)
    lpc = Column('last_password_change', DateTime())
    lpc.create(account)


def downgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)
    account = Table('galaxy_user', meta, autoload=True)
    account.c.last_password_change.drop()
