"""add index workflow_request_input_parameters__workflow_invocation_id

Revision ID: caa7742f7bca
Revises: 3a2914d703ca
Create Date: 2023-03-07 15:10:44.943542

"""

from galaxy.model.database_object_names import build_index_name
from galaxy.model.migrations.util import (
    create_index,
    drop_index,
)

# revision identifiers, used by Alembic.
revision = "caa7742f7bca"
down_revision = "3a2914d703ca"
branch_labels = None
depends_on = None


table_name = "workflow_request_input_parameters"
column_name = "workflow_invocation_id"
index_name = build_index_name(table_name, column_name)


def upgrade():
    create_index(index_name, table_name, [column_name])


def downgrade():
    drop_index(index_name, table_name)
