"""Add index on history_dataset_association extension

Revision ID: 55f02fd8ab6c
Revises: 2dc3386d091f
Create Date: 2024-03-25 11:14:40.005394

"""

from galaxy.model.database_object_names import build_index_name
from galaxy.model.migrations.util import (
    create_index,
    drop_index,
)

# revision identifiers, used by Alembic.
revision = "55f02fd8ab6c"
down_revision = "2dc3386d091f"
branch_labels = None
depends_on = None


hda_table_name = "history_dataset_association"
hda_extension_column_name = "extension"
hda_extension_index_name = build_index_name(hda_table_name, hda_extension_column_name)


def upgrade():
    create_index(hda_extension_index_name, hda_table_name, [hda_extension_column_name])


def downgrade():
    drop_index(hda_extension_index_name, hda_table_name)
