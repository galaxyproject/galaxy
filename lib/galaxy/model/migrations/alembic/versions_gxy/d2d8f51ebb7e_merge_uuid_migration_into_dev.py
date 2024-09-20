"""Merge uuid migration into dev

Revision ID: d2d8f51ebb7e
Revises: 04288b6a5b25, eee9229a9765, d4a650f47a3c
Create Date: 2024-09-20 10:52:07.695199

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2d8f51ebb7e'
down_revision = ('04288b6a5b25', 'eee9229a9765')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
