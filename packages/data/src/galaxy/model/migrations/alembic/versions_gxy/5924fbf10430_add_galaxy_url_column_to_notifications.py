"""add galaxy_url column to notifications

Revision ID: 5924fbf10430
Revises: 303a5583a030
Create Date: 2024-04-11 09:56:26.200231

"""

from sqlalchemy import (
    Column,
    String,
)

from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "5924fbf10430"
down_revision = "303a5583a030"
branch_labels = None
depends_on = None


# database object names used in this revision
table_name = "notification"
column_name = "galaxy_url"


def upgrade():
    add_column(table_name, Column(column_name, String(255)))


def downgrade():
    drop_column(table_name, column_name)
