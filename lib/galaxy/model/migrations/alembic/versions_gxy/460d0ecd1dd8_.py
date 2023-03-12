"""Merge head revisions

COMMENT: After merging 23.0 into dev in 0ac48236df7984ae2c74d6d0470a6b0aec8e9cc6,
the gxy branch was split at revision c29f into 2 conflicting branches, each
having 2 revisions on top of c29f. This revision merges the diverged branches
back into one branch.

Revision ID: 460d0ecd1dd8
Revises: caa7742f7bca, 9540a051226e
Create Date: 2023-03-11 19:40:06.135368

"""

# revision identifiers, used by Alembic.
revision = "460d0ecd1dd8"
down_revision = ("caa7742f7bca", "9540a051226e")
branch_labels = None
depends_on = None


def upgrade():
    # Intentionally empty
    pass


def downgrade():
    # Intentionally empty
    pass
