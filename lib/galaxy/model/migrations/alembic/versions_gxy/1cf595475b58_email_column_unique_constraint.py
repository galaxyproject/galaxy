"""Email column unique constraint

Revision ID: 1cf595475b58
Revises: d619fdfa6168
Create Date: 2024-07-03 19:53:22.443016

Upgrade note: This upgrade will raise an error if there are duplicate email
values in the galaxy_user table. In that case, duplicate values should be
removed. For that, run the email deduplication script availbable in the data
package.
"""

from galaxy.model.database_object_names import (
    build_index_name,
    build_unique_constraint_name,
)
from galaxy.model.migrations.util import (
    create_index,
    create_unique_constraint,
    drop_constraint,
    drop_index,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "1cf595475b58"
down_revision = "d619fdfa6168"
branch_labels = None
depends_on = None


table_name = "galaxy_user"
column_name = "email"
constraint_name = build_unique_constraint_name(table_name, [column_name])
index_name = build_index_name(table_name, [column_name])


def upgrade():
    with transaction():
        create_unique_constraint(constraint_name, table_name, [column_name])
        drop_index(index_name, table_name)  # the unique constraint provides an index


def downgrade():
    drop_constraint(constraint_name, table_name)
    create_index(index_name, table_name, [column_name])
