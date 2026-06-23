"""add index workflow_request_step_states__workflow_invocation_id

Revision ID: 3a2914d703ca
Revises: c39f1de47a04
Create Date: 2023-03-07 15:06:55.682273

"""

from galaxy.model.database_object_names import build_index_name
from galaxy.model.migrations.util import (
    create_index,
    drop_index,
)

# revision identifiers, used by Alembic.
revision = "3a2914d703ca"
down_revision = "c39f1de47a04"
branch_labels = None
depends_on = None

table_name = "workflow_request_step_states"
column_name = "workflow_invocation_id"
index_name = build_index_name(table_name, column_name)


def upgrade():
    create_index(index_name, table_name, [column_name])


def downgrade():
    drop_index(index_name, table_name)
