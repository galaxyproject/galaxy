"""
The NCBI BLAST+ tools have been eliminated from the distribution.  The tools and
datatypes are now available in repositories named ncbi_blast_plus and
blast_datatypes, in the main Galaxy tool shed at http://toolshed.g2.bx.psu.edu.
These repositories will be installed into your local Galaxy instance at the
location discussed above by running the following command.
"""

import sys

def upgrade(migrate_engine):
    print __doc__
def downgrade(migrate_engine):
    pass
