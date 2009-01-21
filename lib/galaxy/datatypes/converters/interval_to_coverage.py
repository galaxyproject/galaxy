#!/usr/bin/env python
"""
Converter to generate 3 (or 4) column base-pair coverage from an interval file.

usage: %prog bed_file out_file
    -1, --cols1=N,N,N,N: Columns for chrom, start, end, strand in interval file
    -2, --cols2=N,N,N,N: Columns for chrom, start, end, strand in coverage file
"""
import sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.intervals import io
from bx.cookbook import doc_optparse

INTERVAL_METADATA = ('chromCol',
                     'startCol',
                     'endCol',
                     'strandCol',)

COVERAGE_METADATA = ('chromCol',
                     'positionCol',
                     'forwardCol',
                     'reverseCol',)

def main( interval, coverage ):
    chroms = dict()
    for record in interval:
        if not type( record ) is io.GenomicInterval: continue
        chrom = chroms[record.chrom] = chroms.get(record.chrom, dict())
        for position in xrange(record.start, record.end):
            coverages = chrom[position] = chrom.get(position,[0,0])
            if record.strand == "-": coverages[1] += 1
            else: coverages[0] += 1
    for chrom in sorted(chroms.iterkeys()):
        positions = chroms[chrom]
        for position in sorted(positions.iterkeys()):
            coverage.write( chrom=chrom, position=position, forward=positions[position][0], reverse=positions[position][1] )

class CoverageWriter( object ):
    def __init__( self, out_stream=None, chromCol=0, positionCol=1, forwardCol=2, reverseCol=3 ):
        self.chromCol, self.positionCol, self.forwardCol, self.reverseCol = chromCol, positionCol, forwardCol, reverseCol
        self.nfields = max( chromCol, positionCol, forwardCol, reverseCol )+1
        self.out_stream = out_stream
        self.nlines = 0
        
    def write(self, chrom="chr", position=0, forward=0, reverse=0 ):
        self.nlines += 1
        if self.nlines % 64000: self.out_stream.flush()
        outlist = [None] * self.nfields
        outlist[self.chromCol] = str(chrom)
        outlist[self.positionCol] = str(position)
        if self.reverseCol == -1: outlist[self.forwardCol] = str(forward + reverse)
        else: 
            outlist[self.forwardCol] = str(forward)
            outlist[self.reverseCol] = str(reverse)
        self.out_stream.write("%s\n" % "\t".join( outlist ))
        
    def flush(self):
        self.out_stream.flush()

if __name__ == "__main__":
    options, args = doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = [int(x)-1 for x in options.cols1.split(',')]
        chr_col_2, position_col_2, forward_col_2, reverse_col_2 = [int(x)-1 for x in options.cols2.split(',')]      
        in_fname, out_fname = args
    except:
        doc_optparse.exception()

    coverage = CoverageWriter( out_stream = open(out_fname, "a"),
                               chromCol = chr_col_2, positionCol = position_col_2,
                               forwardCol = forward_col_2, reverseCol = reverse_col_2, )
    interval = io.NiceReaderWrapper( open(in_fname, "r"), 
                                     chrom_col=chr_col_1,
                                     start_col=start_col_1,
                                     end_col=end_col_1,
                                     strand_col=strand_col_1,
                                     fix_strand=True )
    main( interval, coverage )
    coverage.flush()