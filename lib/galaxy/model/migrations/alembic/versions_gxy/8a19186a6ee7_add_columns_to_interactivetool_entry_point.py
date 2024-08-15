"""add label, requires_path_in_url and requires_path_in_header_named columns to interactivetool_entry_point

Revision ID: 8a19186a6ee7
Revises: ddbdbc40bdc1
Create Date: 2023-11-15 12:53:32.888292

"""

from sqlalchemy import (
    Boolean,
    Column,
    Text,
)

from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "8a19186a6ee7"
down_revision = "ddbdbc40bdc1"
branch_labels = None
depends_on = None

# database object names used in this revision
table_name = "interactivetool_entry_point"
label_column_name = "label"
requires_path_in_url_colname = "requires_path_in_url"
requires_path_in_header_named_colname = "requires_path_in_header_named"


def upgrade():
    add_column(table_name, Column(label_column_name, Text()))
    add_column(table_name, Column(requires_path_in_url_colname, Boolean(), default=False))
    add_column(table_name, Column(requires_path_in_header_named_colname, Text()))


def downgrade():
    drop_column(table_name, requires_path_in_header_named_colname)
    drop_column(table_name, requires_path_in_url_colname)
    drop_column(table_name, label_column_name)
