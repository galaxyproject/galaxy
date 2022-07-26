"""add bar3 table

Revision ID: 0e28bf2fb7b5
Revises: 8364ef1cab05
Create Date: 2021-11-05 16:31:00.530235

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0e28bf2fb7b5"
down_revision = "8364ef1cab05"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tsi_table3",
        sa.Column("id", sa.Integer, primary_key=True),
    )


def downgrade():
    op.drop_table("tsi_table3")
