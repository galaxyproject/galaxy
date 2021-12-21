"""create table1 gxy

Revision ID: 5a48ba88c465
Revises: e7b6dcb09efd
Create Date: 2021-12-28 12:04:46.418576

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a48ba88c465'
down_revision = 'e7b6dcb09efd'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'gxy_table1',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('data', sa.String),
    )


def downgrade():
    op.drop_table('gxy_table1')
