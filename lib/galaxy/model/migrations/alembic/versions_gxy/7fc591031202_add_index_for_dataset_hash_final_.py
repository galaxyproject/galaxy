"""Add index to speed up matching on DatasetHash rows

Revision ID: 7fc591031202
Revises: 64d49ad328d4
Create Date: 2026-10-09 12:49:17.362096

"""

from galaxy.model.database_object_names import build_index_name
from galaxy.model.migrations.util import (
    create_index,
    drop_index,
)

# revision identifiers, used by Alembic.
revision = "7fc591031202"
down_revision = "64d49ad328d4"
branch_labels = None
depends_on = None


table_name = "dataset_hash"
column_names = ["extra_files_path", "hash_function", "hash_value"]
index_name = build_index_name(table_name, column_names)
mysql_length = dict.fromkeys(column_names, 200)


def upgrade() -> None:
    create_index(index_name, table_name, column_names, mysql_length=mysql_length)


def downgrade() -> None:
    drop_index(index_name, table_name)
