"""add_indexes_for_workflow_comment_foreign_keys

Revision ID: 2dc3386d091f
Revises: 8a19186a6ee7
Create Date: 2024-03-13 15:25:52.587488

"""

from galaxy.model.database_object_names import build_index_name
from galaxy.model.migrations.util import (
    create_index,
    drop_index,
)

# revision identifiers, used by Alembic.
revision = "2dc3386d091f"
down_revision = "8a19186a6ee7"
branch_labels = None
depends_on = None

workflow_comment_table_name = "workflow_comment"
workflow_step_table_name = "workflow_step"
workflow_id_column_name = "workflow_id"
parent_comment_id_column_name = "parent_comment_id"

workflow_step_parent_comment_index_name = build_index_name(workflow_step_table_name, parent_comment_id_column_name)
workflow_comment_workflow_id_index_name = build_index_name(workflow_comment_table_name, workflow_id_column_name)
workflow_comment_parent_comment_index_name = build_index_name(
    workflow_comment_table_name, parent_comment_id_column_name
)


def upgrade():
    create_index(workflow_step_parent_comment_index_name, workflow_step_table_name, [parent_comment_id_column_name])
    create_index(workflow_comment_workflow_id_index_name, workflow_comment_table_name, [workflow_id_column_name])
    create_index(
        workflow_comment_parent_comment_index_name, workflow_comment_table_name, [parent_comment_id_column_name]
    )


def downgrade():
    drop_index(workflow_step_parent_comment_index_name, workflow_step_table_name)
    drop_index(workflow_comment_workflow_id_index_name, workflow_comment_table_name)
    drop_index(workflow_comment_parent_comment_index_name, workflow_comment_table_name)
