"""add foo3 table

Revision ID: e02cef55763c
Revises: 2e8a580bc79a
Create Date: 2021-11-05 16:30:30.521436

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e02cef55763c"
down_revision = "2e8a580bc79a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "gxy_table3",
        sa.Column("id", sa.Integer, primary_key=True),
    )


def downgrade():
    op.drop_table("gxy_table3")
