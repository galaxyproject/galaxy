"""Implement fixed length collection types.

Revision ID: ec25b23b08e2
Revises: caeee878d7cd
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
down_revision = "caeee878d7cd"
branch_labels = None
depends_on = None

dataset_collection_element_table = "dataset_collection_element"
dataset_collection_table = "dataset_collection"
job_to_input_dataset_table = "job_to_input_dataset"
job_to_input_dataset_collection_table = "job_to_input_dataset_collection"
job_to_input_dataset_collection_element_table = "job_to_input_dataset_collection_element"


def upgrade():
    with transaction():
        add_column(dataset_collection_table, Column("fields", JSONType(), default=None))

        add_column(job_to_input_dataset_table, Column("adapter", JSONType(), default=None))
        add_column(job_to_input_dataset_collection_table, Column("adapter", JSONType(), default=None))
        add_column(job_to_input_dataset_collection_element_table, Column("adapter", JSONType(), default=None))


def downgrade():
    with transaction():
        drop_column(dataset_collection_table, "fields")

        drop_column(job_to_input_dataset_table, "adapter")
        drop_column(job_to_input_dataset_collection_table, "adapter")
        drop_column(job_to_input_dataset_collection_element_table, "adapter")
