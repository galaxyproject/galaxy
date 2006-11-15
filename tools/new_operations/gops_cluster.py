#!/usr/bin/env python

"""
Cluster regions of intervals.

usage: %prog in_file out_file
    -1, --cols1=N,N,N,N: Columns for start, end, strand in file
    -d, --distance=N: Maximum distance between clustered intervals
    -v, --overlap=N: Minimum overlap require (negative distance)
    -m, --minregions=N: Minimum regions per cluster
    -o, --output=N: 1)merged 2)filtered 3)clustered
"""

import pkg_resources
pkg_resources.require( "bx-python" )

import sys
import traceback
import fileinput
from warnings import warn

from bx.intervals import *
from bx.intervals.io import *
from bx.intervals.operations.find_clusters import *
import cookbook.doc_optparse

from galaxyops import *

def main():
    distance = 0
    minregions = 2
    output = 1
    upstream_pad = 0
    downstream_pad = 0

    options, args = cookbook.doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        if options.distance: distance = int( options.distance )
        if options.overlap: distance = -1 * int( options.overlap )
        if options.output: output = int( options.output )
        if options.minregions: minregions = int( options.minregions )
        in_fname, out_fname = args
    except:
        cookbook.doc_optparse.exception()

    f1 = fileinput.FileInput( in_fname )
    g1 = GenomicIntervalReader( f1,
                                chrom_col=chr_col_1,
                                start_col=start_col_1,
                                end_col=end_col_1,
                                strand_col=strand_col_1)

    out_file = open( out_fname, "w" )

    # Get the cluster tree
    clusters, extra = find_clusters( g1, mincols=distance, minregions=minregions)
    f1.close()

    f1 = open( in_fname, "r" )
    
    # If "merge"
    if output == 1:
        fields = ["."  for x in range(max(g1.chrom_col, g1.start_col, g1.end_col)+1)]
        for chrom, tree in clusters.items():
            for start, end in tree.getregions():
                fields[g1.chrom_col] = chrom
                fields[g1.start_col] = str(start)
                fields[g1.end_col] = str(end)
                print >> out_file, "\t".join( fields )

    # If "filtered" we preserve order of file and comments, etc.
    if output == 2:
        linenums = dict()
        for chrom, tree in clusters.items():
            for linenum in tree.getlines():
                linenums[linenum] = 0
        linenum = -1
        f1.seek(0)
        for line in f1.readlines():
            linenum += 1
            if linenum in linenums or linenum in extra:
                print >> out_file, line.rstrip("\n\r")

    # If "clustered" we output original intervals, but near each other (i.e. clustered)
    if output == 3:
        linenums = list()
        f1.seek(0)
        fileLines = f1.readlines()
        for chrom, tree in clusters.items():
            for linenum in tree.getlines():
                print >> out_file, fileLines[linenum].rstrip("\n\r")

    f1.close()
    
if __name__ == "__main__":
    main()
