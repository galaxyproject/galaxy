"""create table vault

Revision ID: 40aaada107df
Revises: e7b6dcb09efd
Create Date: 2022-01-19 10:47:47.135278

"""
import datetime

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '40aaada107df'
down_revision = 'e7b6dcb09efd'
branch_labels = None
depends_on = None


def upgrade():
    now = datetime.datetime.utcnow
    op.create_table('vault',
        sa.Column('key', sa.Text, primary_key=True),
        sa.Column('parent_key', sa.Text, sa.ForeignKey('vault.key'), index=True, nullable=True),
        sa.Column('value', sa.Text, nullable=True),
        sa.Column("create_time", sa.DateTime, default=now),
        sa.Column("update_time", sa.DateTime, default=now, onupdate=now),
    )


def downgrade():
    op.drop_table('vault')
