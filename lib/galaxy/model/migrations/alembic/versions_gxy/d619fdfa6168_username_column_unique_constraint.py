"""Username column unique constraint

Revision ID: d619fdfa6168
Revises: eee9229a9765
Create Date: 2024-07-02 13:13:10.325586

Upgrade note: This upgrade will raise an error if there are duplicate username
values in the galaxy_user table. In that case, duplicate values should be
removed. For that, run the username deduplication script availbable in the data
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
revision = "d619fdfa6168"
down_revision = "eee9229a9765"
branch_labels = None
depends_on = None

table_name = "galaxy_user"
column_name = "username"
constraint_name = build_unique_constraint_name(table_name, [column_name])
index_name = build_index_name(table_name, [column_name])


def upgrade():
    with transaction():
        create_unique_constraint(constraint_name, table_name, [column_name])
        drop_index(index_name, table_name)  # the unique constraint provides an index


def downgrade():
    drop_constraint(constraint_name, table_name)
    create_index(index_name, table_name, [column_name])
