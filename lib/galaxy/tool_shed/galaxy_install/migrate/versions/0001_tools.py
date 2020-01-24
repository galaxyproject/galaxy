"""
Initialize the version column of the migrate_tools database table to 1.  No tool migrations are handled in this version.
"""
from __future__ import print_function


def upgrade(migrate_engine):
    print(__doc__)


def downgrade(migrate_engine):
    pass
