"""create table3 gxy

Revision ID: 81530479f98a
Revises: 5b8a688ac602
Create Date: 2021-12-28 12:24:12.593103

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '81530479f98a'
down_revision = '5b8a688ac602'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
       'gxy_table3',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('data', sa.String),
    )


def downgrade():
    op.drop_table('gxy_table3')
