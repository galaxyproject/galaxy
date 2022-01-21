"""create table vault

Revision ID: 40aaada107df
Revises: e7b6dcb09efd
Create Date: 2022-01-19 10:47:47.135278

"""
import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = '40aaada107df'
down_revision = 'e7b6dcb09efd'
branch_labels = None
depends_on = None


def upgrade():
    # This is the last revision to the database that was handled with SQLAlchemy Migrate prior to
    # the move to Alembic. However, it was added to the dev branch after 21.09 was released, but
    # before 22.01. Therefore, this table should be created when upgrading from 21.09, but not from dev.
    if not _table_exists('vault'):
        now = datetime.datetime.utcnow
        op.create_table('vault',
            sa.Column('key', sa.Text, primary_key=True),
            sa.Column('parent_key', sa.Text, sa.ForeignKey('vault.key'), index=True, nullable=True),
            sa.Column('value', sa.Text, nullable=True),
            sa.Column("create_time", sa.DateTime, default=now),
            sa.Column("update_time", sa.DateTime, default=now, onupdate=now),
        )


def downgrade():
    # See comment in upgrade function
    if _table_exists('vault'):
        op.drop_table('vault')


def _table_exists(table: str):
    inspector = Inspector.from_engine(op.get_bind())
    return table in inspector.get_table_names()
