"""
The tools "Map with BWA for Illumina" and "Map with BWA for SOLiD" have
been eliminated from the distribution.  The tools are now available
in the repository named bwa_wrappers from the main Galaxy tool shed at
http://toolshed.g2.bx.psu.edu, and will be installed into your local
Galaxy instance at the location discussed above by running the following
command.
"""
from __future__ import print_function


def upgrade(migrate_engine):
    print(__doc__)


def downgrade(migrate_engine):
    pass
