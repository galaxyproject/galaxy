"""create table2 gxy

Revision ID: 5b8a688ac602
Revises: 5a48ba88c465
Create Date: 2021-12-28 12:24:00.123210

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5b8a688ac602'
down_revision = '5a48ba88c465'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'gxy_table2',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('data', sa.String),
    )


def downgrade():
    op.drop_table('gxy_table2')
