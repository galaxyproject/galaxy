#!/usr/bin/env python

import sys
from galaxy import eggs
from galaxy.datatypes.util.gff_util import read_unordered_gtf

# Older py compatibility
try:
    set()
except:
    from sets import Set as set

assert sys.version_info[:2] >= ( 2, 4 )

#
# Process inputs.
#

in_fname = sys.argv[1]
out_fname = sys.argv[2]

out = open( out_fname, 'w' )
for feature in read_unordered_gtf( open( in_fname, 'r' ) ):
    # Print feature.
    for interval in feature.intervals:
        out.write( "\t".join(interval.fields) )
out.close()

# TODO: print status information: how many lines processed and features found.