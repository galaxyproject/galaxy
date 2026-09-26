"""Add on-delete to fkey on galaxy_session_to_history.session_id

Revision ID: caeee878d7cd
Revises: 0c681a59dce1
Create Date: 2025-03-22 11:53:01.514335

"""

from galaxy.model.database_object_names import build_foreign_key_name
from galaxy.model.migrations.util import (
    create_foreign_key,
    drop_constraint,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "caeee878d7cd"
down_revision = "0c681a59dce1"
branch_labels = None
depends_on = None

session_table = "galaxy_session"
job_table = "galaxy_session_to_history"
session_id_column = "session_id"

job_session_fk = build_foreign_key_name(job_table, session_id_column)
fkey_args = (job_session_fk, job_table, session_table, [session_id_column], ["id"])


def upgrade():
    with transaction():
        drop_constraint(job_session_fk, job_table)
        create_foreign_key(*fkey_args, ondelete="CASCADE")


def downgrade():
    pass
    with transaction():
        drop_constraint(job_session_fk, job_table)
        create_foreign_key(*fkey_args)
