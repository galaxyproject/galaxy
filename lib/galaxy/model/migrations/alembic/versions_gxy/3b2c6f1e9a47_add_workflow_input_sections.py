"""Add workflow input sections

Revision ID: 3b2c6f1e9a47
Revises: 64d49ad328d4
Create Date: 2026-11-04 12:00:00.000000

"""

import sqlalchemy as sa

from galaxy.model.custom_types import JSONType
from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "3b2c6f1e9a47"
down_revision = "64d49ad328d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column("workflow", sa.Column("input_sections", JSONType, nullable=True))
    add_column("workflow_step", sa.Column("input_section", sa.Unicode(255), nullable=True))


def downgrade() -> None:
    drop_column("workflow_step", "input_section")
    drop_column("workflow", "input_sections")
