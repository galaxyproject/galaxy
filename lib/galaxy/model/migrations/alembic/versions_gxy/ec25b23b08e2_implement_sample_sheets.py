"""Implement sample sheets.

Revision ID: ec25b23b08e2
Revises: 75348cfb3715
Create Date: 2024-12-09 10:28:54.902847

"""

from sqlalchemy import Column

from galaxy.model.custom_types import JSONType
from galaxy.model.migrations.util import (
    add_column,
    drop_column,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "ec25b23b08e2"
down_revision = "75348cfb3715"
branch_labels = None
depends_on = None

dataset_collection_element_table = "dataset_collection_element"
dataset_collection_table = "dataset_collection"


def upgrade():
    with transaction():
        add_column(dataset_collection_table, Column("column_definitions", JSONType(), default=None))
        add_column(dataset_collection_element_table, Column("columns", JSONType(), default=None))


def downgrade():
    with transaction():
        drop_column(dataset_collection_table, "column_definitions")
        drop_column(dataset_collection_element_table, "columns")
