#!/usr/bin/env python
# This tool takes a gff file as input and counts the number of features in it.

import sys, fileinput
from galaxy import eggs
from galaxy.datatypes.util.gff_util import GFFReaderWrapper
from bx.intervals.io import GenomicInterval

# Get args.
input_file = sys.argv[1:]

# Count features.
count = 0
for feature in GFFReaderWrapper( fileinput.FileInput( input_file ), fix_strand=True ):
    if isinstance( feature, GenomicInterval ):
        count += 1

print count