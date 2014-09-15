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
import psyco_full
import commands
import os
from os import environ
import tempfile
from bisect import bisect

INTERVAL_METADATA = ('chromCol',
                     'startCol',
                     'endCol',
                     'strandCol',)

COVERAGE_METADATA = ('chromCol',
                     'positionCol',
                     'forwardCol',
                     'reverseCol',)

def main( interval, coverage ):
    """
    Uses a sliding window of partitions to count coverages.
    Every interval record adds its start and end to the partitions.  The result
    is a list of partitions, or every position that has a (maybe) different
    number of basepairs covered.  We don't worry about merging because we pop
    as the sorted intervals are read in.  As the input start positions exceed
    the partition positions in partitions, coverages are kicked out in bulk.
    """
    partitions = []
    forward_covs = []
    reverse_covs = []
    offset = 0
    chrom = None
    lastchrom = None
    for record in interval:
        chrom = record.chrom
        if lastchrom and not lastchrom == chrom and partitions:
            for partition in xrange(0, len(partitions)-1):
                forward = forward_covs[partition]
                reverse = reverse_covs[partition]
                if forward+reverse > 0:
                    coverage.write(chrom=chrom, position=xrange(partitions[partition],partitions[partition+1]),
                                   forward=forward, reverse=reverse)
            partitions = []
            forward_covs = []
            reverse_covs = []

        start_index = bisect(partitions, record.start)
        forward = int(record.strand == "+")
        reverse = int(record.strand == "-")
        forward_base = 0
        reverse_base = 0
        if start_index > 0:
            forward_base = forward_covs[start_index-1]
            reverse_base = reverse_covs[start_index-1]
        partitions.insert(start_index, record.start)
        forward_covs.insert(start_index, forward_base)
        reverse_covs.insert(start_index, reverse_base)
        end_index = bisect(partitions, record.end)
        for index in xrange(start_index, end_index):
            forward_covs[index] += forward
            reverse_covs[index] += reverse
        partitions.insert(end_index, record.end)
        forward_covs.insert(end_index, forward_covs[end_index-1] - forward )
        reverse_covs.insert(end_index, reverse_covs[end_index-1] - reverse )

        if partitions:
            for partition in xrange(0, start_index):
                forward = forward_covs[partition]
                reverse = reverse_covs[partition]
                if forward+reverse > 0:
                    coverage.write(chrom=chrom, position=xrange(partitions[partition],partitions[partition+1]),
                                   forward=forward, reverse=reverse)
            partitions = partitions[start_index:]
            forward_covs = forward_covs[start_index:]
            reverse_covs = reverse_covs[start_index:]

        lastchrom = chrom

    # Finish the last chromosome
    if partitions:
        for partition in xrange(0, len(partitions)-1):
            forward = forward_covs[partition]
            reverse = reverse_covs[partition]
            if forward+reverse > 0:
                coverage.write(chrom=chrom, position=xrange(partitions[partition],partitions[partition+1]),
                               forward=forward, reverse=reverse)

class CoverageWriter( object ):
    def __init__( self, out_stream=None, chromCol=0, positionCol=1, forwardCol=2, reverseCol=3 ):
        self.out_stream = out_stream
        self.reverseCol = reverseCol
        self.nlines = 0
        positions = {str(chromCol):'%(chrom)s',
                     str(positionCol):'%(position)d',
                     str(forwardCol):'%(forward)d',
                     str(reverseCol):'%(reverse)d'}
        if reverseCol < 0:
            self.template = "%(0)s\t%(1)s\t%(2)s\n" % positions
        else:
            self.template = "%(0)s\t%(1)s\t%(2)s\t%(3)s\n" % positions

    def write(self, **kwargs ):
        if self.reverseCol < 0: kwargs['forward'] += kwargs['reverse']
        posgen = kwargs['position']
        for position in posgen:
            kwargs['position'] = position
            self.out_stream.write(self.template % kwargs)

    def close(self):
        self.out_stream.flush()
        self.out_stream.close()

if __name__ == "__main__":
    options, args = doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = [int(x)-1 for x in options.cols1.split(',')]
        chr_col_2, position_col_2, forward_col_2, reverse_col_2 = [int(x)-1 for x in options.cols2.split(',')]
        in_fname, out_fname = args
    except:
        doc_optparse.exception()

    # Sort through a tempfile first
    temp_file = tempfile.NamedTemporaryFile(mode="r")
    environ['LC_ALL'] = 'POSIX'
    commandline = "sort -f -n -k %d -k %d -k %d -o %s %s" % (chr_col_1+1,start_col_1+1,end_col_1+1, temp_file.name, in_fname)
    errorcode, stdout = commands.getstatusoutput(commandline)

    coverage = CoverageWriter( out_stream = open(out_fname, "a"),
                               chromCol = chr_col_2, positionCol = position_col_2,
                               forwardCol = forward_col_2, reverseCol = reverse_col_2, )
    temp_file.seek(0)
    interval = io.NiceReaderWrapper( temp_file,
                                     chrom_col=chr_col_1,
                                     start_col=start_col_1,
                                     end_col=end_col_1,
                                     strand_col=strand_col_1,
                                     fix_strand=True )
    main( interval, coverage )
    temp_file.close()
    coverage.close()
