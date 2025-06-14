"""Implement sample sheets

Revision ID: 3af58c192752
Revises: fb16d09348db
Create Date: 2025-01-09 10:35:08.825159

"""

from sqlalchemy import Column

from galaxy.model.custom_types import JSONType
from galaxy.model.migrations.util import (
    add_column,
    drop_column,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "3af58c192752"
down_revision = "fb16d09348db"
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
