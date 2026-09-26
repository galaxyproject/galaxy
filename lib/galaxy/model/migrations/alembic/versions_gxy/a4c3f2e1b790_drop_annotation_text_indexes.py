"""Drop whole-text annotation indexes.

Revision ID: a4c3f2e1b790
Revises: e96dd6fd5863
Create Date: 2026-09-17
"""

from galaxy.model.migrations.util import (
    create_index,
    drop_index,
)

revision = "a4c3f2e1b790"
down_revision = "e96dd6fd5863"
branch_labels = None
depends_on = None

ANNOTATION_INDEXES = (
    ("history_annotation_association", "ix_history_anno_assoc_annotation"),
    ("history_dataset_association_annotation_association", "ix_history_dataset_anno_assoc_annotation"),
    ("stored_workflow_annotation_association", "ix_stored_workflow_ann_assoc_annotation"),
    ("workflow_step_annotation_association", "ix_workflow_step_ann_assoc_annotation"),
    ("page_annotation_association", "ix_page_annotation_association_annotation"),
    ("visualization_annotation_association", "ix_visualization_annotation_association_annotation"),
)


def upgrade():
    # PostgreSQL B-tree entries have a size limit even when the column is TEXT.
    # Annotation lookups use the item/user indexes, not the annotation value.
    for table_name, index_name in ANNOTATION_INDEXES:
        drop_index(index_name, table_name)


def downgrade():
    # PostgreSQL cannot restore these indexes if oversized annotations have been
    # saved since upgrading; leave that failure explicit rather than alter data.
    for table_name, index_name in ANNOTATION_INDEXES:
        create_index(index_name, table_name, ["annotation"], mysql_length=200)
