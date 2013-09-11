"""
The following tools have been eliminated from the distribution:
Map with Bowtie for Illumina, Map with Bowtie for SOLiD, Lastz,
and Lastz paired reads.  The tools are now available in the
repositories named bowtie_wrappers, bowtie_color_wrappers, lastz,
and lastz_paired_reads from the main Galaxy tool shed at
http://toolshed.g2.bx.psu.edu, and will be installed into your
local Galaxy instance at the location discussed above by running
the following command.
"""

import sys

def upgrade(migrate_engine):
    print __doc__
def downgrade(migrate_engine):
    pass
