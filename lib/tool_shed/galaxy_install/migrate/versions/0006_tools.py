"""
The following tools have been eliminated from the distribution:
FASTQ to BAM, SAM to FASTQ, BAM Index Statistics, Estimate Library
Complexity, Insertion size metrics for PAIRED data, SAM/BAM Hybrid
Selection Metrics, bam/sam Cleaning, Add or Replace Groups, Replace
SAM/BAM Header, Paired Read Mate Fixer, Mark Duplicate reads,
SAM/BAM Alignment Summary Metrics, SAM/BAM GC Bias Metrics, and
Reorder SAM/BAM.  The tools are now available in the repository
named picard from the main Galaxy tool shed at
http://toolshed.g2.bx.psu.edu, and will be installed into your
local Galaxy instance at the location discussed above by running
the following command.
"""

import sys

def upgrade(migrate_engine):
    print __doc__
def downgrade(migrate_engine):
    pass
