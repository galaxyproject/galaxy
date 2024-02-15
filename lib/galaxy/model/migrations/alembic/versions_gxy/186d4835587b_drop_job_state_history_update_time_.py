"""drop job_state_history.update_time column

Revision ID: 186d4835587b
Revises: 6a67bf27e6a6
Create Date: 2022-06-01 17:50:22.629894

"""

from sqlalchemy import (
    Column,
    DateTime,
)

from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)
from galaxy.model.orm.now import now

# revision identifiers, used by Alembic.
revision = "186d4835587b"
down_revision = "6a67bf27e6a6"
branch_labels = None
depends_on = None

table_name = "job_state_history"
column_name = "update_time"


def upgrade():
    drop_column(table_name, column_name)


def downgrade():
    add_column(table_name, Column(column_name, DateTime, default=now, onupdate=now))
