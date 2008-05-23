#!/usr/bin/env python
"""
Cluster regions of intervals.

usage: %prog in_file out_file
    -1, --cols1=N,N,N,N: Columns for start, end, strand in file
    -d, --distance=N: Maximum distance between clustered intervals
    -v, --overlap=N: Minimum overlap require (negative distance)
    -m, --minregions=N: Minimum regions per cluster
    -o, --output=N: 1)merged 2)filtered 3)clustered 4) minimum 5) maximum
"""
from galaxy import eggs
import pkg_resources
pkg_resources.require( "bx-python" )
import sys, traceback, fileinput
from warnings import warn
from bx.intervals import *
from bx.intervals.io import *
from bx.intervals.operations.find_clusters import *
from bx.cookbook import doc_optparse
from galaxy.tools.util.galaxyops import *

assert sys.version_info[:2] >= ( 2, 4 )

def main():
    distance = 0
    minregions = 2
    output = 1
    upstream_pad = 0
    downstream_pad = 0

    options, args = doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        if options.distance: distance = int( options.distance )
        if options.overlap: distance = -1 * int( options.overlap )
        if options.output: output = int( options.output )
        if options.minregions: minregions = int( options.minregions )
        in_fname, out_fname = args
    except:
        doc_optparse.exception()

    g1 = NiceReaderWrapper( fileinput.FileInput( in_fname ),
                            chrom_col=chr_col_1,
                            start_col=start_col_1,
                            end_col=end_col_1,
                            strand_col=strand_col_1,
                            fix_strand=True )

    # Get the cluster tree
    try:
        clusters, extra = find_clusters( g1, mincols=distance, minregions=minregions)
    except ParseError, exc:
        fail( "Invalid file format: %s" % str( exc ) )

    f1 = open( in_fname, "r" )
    out_file = open( out_fname, "w" )
    
    # If "merge"
    if output == 1:
        fields = ["."  for x in range(max(g1.chrom_col, g1.start_col, g1.end_col)+1)]
        for chrom, tree in clusters.items():
            for start, end, lines in tree.getregions():
                fields[g1.chrom_col] = chrom
                fields[g1.start_col] = str(start)
                fields[g1.end_col] = str(end)
                out_file.write( "%s\n" % "\t".join( fields ) )

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
                out_file.write( "%s\n" % line.rstrip( "\n\r" ) )

    # If "clustered" we output original intervals, but near each other (i.e. clustered)
    if output == 3:
        linenums = list()
        f1.seek(0)
        fileLines = f1.readlines()
        for chrom, tree in clusters.items():
            for linenum in tree.getlines():
                out_file.write( "%s\n" % fileLines[linenum].rstrip( "\n\r" ) )

    # If "minimum" we output the smallest interval in each cluster
    if output == 4 or output == 5:
        linenums = list()
        f1.seek(0)
        fileLines = f1.readlines()
        for chrom, tree in clusters.items():
            regions = tree.getregions()
            for start, end, lines in tree.getregions():
                outsize = -1
                outinterval = None
                for line in lines:
                    # three nested for loops?
                    # should only execute this code once per line
                    fileline = fileLines[line].rstrip("\n\r")
                    try:
                        cluster_interval = GenomicInterval( g1, fileline.split("\t"), 
                                                            g1.chrom_col, 
                                                            g1.start_col,
                                                            g1.end_col, 
                                                            g1.strand_col, 
                                                            g1.default_strand,
                                                            g1.fix_strand )
                    except Exception, exc:
                        print >> sys.stderr, str( exc )
                        f1.close()
                        sys.exit()
                    interval_size = cluster_interval.end - cluster_interval.start
                    if outsize == -1 or \
                       ( outsize > interval_size and output == 4 ) or \
                       ( outsize < interval_size and output == 5 ) :
                        outinterval = cluster_interval
                        outsize = interval_size
                out_file.write( "%s\n" % outinterval )

    f1.close()
    out_file.close()
    
    if g1.skipped > 0:
        print skipped( g1, filedesc="" )

if __name__ == "__main__":
    main()
