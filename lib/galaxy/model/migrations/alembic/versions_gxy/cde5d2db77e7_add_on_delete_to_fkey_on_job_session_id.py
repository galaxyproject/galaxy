"""Add on-delete to fkey on job.session_id

Revision ID: cde5d2db77e7
Revises: b964490175fd
Create Date: 2025-03-21 18:18:07.287968

"""

from galaxy.model.database_object_names import build_foreign_key_name
from galaxy.model.migrations.util import (
    create_foreign_key,
    drop_constraint,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "cde5d2db77e7"
down_revision = "b964490175fd"
branch_labels = None
depends_on = None

session_table = "galaxy_session"
job_table = "job"
session_id_column = "session_id"

job_session_fk = build_foreign_key_name(job_table, session_id_column)
fkey_args = (job_session_fk, job_table, session_table, [session_id_column], ["id"])


def upgrade():
    with transaction():
        drop_constraint(job_session_fk, job_table)
        create_foreign_key(*fkey_args, ondelete="SET NULL")


def downgrade():
    pass
    with transaction():
        drop_constraint(job_session_fk, job_table)
        create_foreign_key(*fkey_args)
