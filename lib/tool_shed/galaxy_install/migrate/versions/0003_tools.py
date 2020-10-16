"""
The freebayes tool has been eliminated from the distribution .  The repository named freebayes from the main
Galaxy tool shed at http://toolshed.g2.bx.psu.edu will be installed into your local Galaxy instance at the
location discussed above by running the following command.
"""
from __future__ import print_function


def upgrade(migrate_engine):
    print(__doc__)


def downgrade(migrate_engine):
    pass
