#!/usr/bin/env python
#Guruprasad Ananda
"""
Calculate count and coverage of one query on another, and append the Coverage and counts to
the last four columns as bases covered, percent coverage, number of completely present features, number of partially present/overlapping features.

usage: %prog bed_file_1 bed_file_2 out_file
    -1, --cols1=N,N,N,N: Columns for chr, start, end, strand in first file
    -2, --cols2=N,N,N,N: Columns for chr, start, end, strand in second file
"""
from galaxy import eggs
import pkg_resources
pkg_resources.require( "bx-python" )
import sys, traceback, fileinput
from warnings import warn
from bx.intervals.io import *
from bx.cookbook import doc_optparse
from bx.intervals.operations import quicksect
from galaxy.tools.util.galaxyops import *

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

def counter(node, start, end):
    global full, partial
    if node.start <= start and node.maxend > start:
        if node.end >= end or (node.start == start and end > node.end > start):
            full += 1
        elif end > node.end > start:
            partial += 1
        if node.left and node.left.maxend > start:
            counter(node.left, start, end)
        if node.right: 
            counter(node.right, start, end)
    elif start < node.start < end:
        if node.end <= end:
            full += 1
        else:
            partial += 1
        if node.left and node.left.maxend > start:
            counter(node.left, start, end)
        if node.right: 
            counter(node.right, start, end)
    else:
        if node.left: 
            counter(node.left, start, end)

def count_coverage( readers, comments=True ):
    primary = readers[0]
    secondary = readers[1]
    secondary_copy = readers[2]
    
    rightTree = quicksect.IntervalTree()
    for item in secondary:
        if type( item ) is GenomicInterval:
            rightTree.insert( item, secondary.linenum, item.fields )
    
    bitsets = secondary_copy.binned_bitsets() 
        
    global full, partial
    
    for interval in primary:
        if type( interval ) is Header:
            yield interval
        if type( interval ) is Comment and comments:
            yield interval
        elif type( interval ) == GenomicInterval:
            chrom = interval.chrom
            start = int(interval.start)
            end = int(interval.end)
            full = 0
            partial = 0
            if chrom not in bitsets:
                bases_covered = 0
                percent = 0.0
                full = 0
                partial = 0
            else:
                bases_covered = bitsets[ chrom ].count_range( start, end-start )
                if (end - start) == 0:
                    percent = 0
                else: 
                    percent = float(bases_covered) / float(end - start)
                if bases_covered:
                    root = rightTree.chroms[chrom]    #root node for the chrom tree
                    counter(root, start, end)
            interval.fields.append(str(bases_covered))
            interval.fields.append(str(percent))
            interval.fields.append(str(full))
            interval.fields.append(str(partial))
            yield interval
    
def main():
    options, args = doc_optparse.parse( __doc__ )
    
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        chr_col_2, start_col_2, end_col_2, strand_col_2 = parse_cols_arg( options.cols2 )      
        in1_fname, in2_fname, out_fname = args
    except:
        stop_err( "Data issue: click the pencil icon in the history item to correct the metadata attributes." )
    
    g1 = NiceReaderWrapper( fileinput.FileInput( in1_fname ),
                            chrom_col=chr_col_1,
                            start_col=start_col_1,
                            end_col=end_col_1,
                            strand_col=strand_col_1,
                            fix_strand=True )
    g2 = NiceReaderWrapper( fileinput.FileInput( in2_fname ),
                            chrom_col=chr_col_2,
                            start_col=start_col_2,
                            end_col=end_col_2,
                            strand_col=strand_col_2,
                            fix_strand=True )
    g2_copy = NiceReaderWrapper( fileinput.FileInput( in2_fname ),
                                 chrom_col=chr_col_2,
                                 start_col=start_col_2,
                                 end_col=end_col_2,
                                 strand_col=strand_col_2,
                                 fix_strand=True )
    

    out_file = open( out_fname, "w" )

    try:
        for line in count_coverage([g1,g2,g2_copy]):
            if type( line ) is GenomicInterval:
                out_file.write( "%s\n" % "\t".join( line.fields ) )
            else:
                out_file.write( "%s\n" % line )
    except ParseError, exc:
        out_file.close()
        fail( str( exc ) )

    out_file.close()

    if g1.skipped > 0:
        print skipped( g1, filedesc=" of 1st dataset" )
    if g2.skipped > 0:
        print skipped( g2, filedesc=" of 2nd dataset" )
    elif g2_copy.skipped > 0:
        print skipped( g2_copy, filedesc=" of 2nd dataset" )
        
if __name__ == "__main__":
    main()
