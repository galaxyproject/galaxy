#!/usr/bin/env python
"""
Generate indices for track browsing of an interval file.

usage: %prog bed_file out_directory
    -1, --cols1=N,N,N,N: Columns for chrom, start, end, strand in interval file
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

def divide( intervals, out_path ):
    current_file = None
    lastchrom = ""
    for line in intervals:
        try:
            chrom = line.chrom
        except AttributeError, e:
            continue
        if not lastchrom == chrom:
            if current_file:
                current_file.flush()
                current_file.close()
            current_file = open( os.path.join( out_path, "%s" % chrom), "a" )
        print >> current_file, "\t".join(line)
        lastchrom = chrom
    current_file.flush()
    current_file.close()

if __name__ == "__main__":
    options, args = doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = [int(x)-1 for x in options.cols1.split(',')]
        in_fname, out_path = args
    except:
        doc_optparse.exception()

    # Sort through a tempfile first
    temp_file = tempfile.NamedTemporaryFile(mode="r")
    environ['LC_ALL'] = 'POSIX'
    commandline = "sort -f -n -k %d -k %d -k %d -o %s %s" % (chr_col_1+1,start_col_1+1,end_col_1+1, temp_file.name, in_fname)
    errorcode, stdout = commands.getstatusoutput(commandline)

    temp_file.seek(0)
    interval = io.NiceReaderWrapper( temp_file, 
                                     chrom_col=chr_col_1,
                                     start_col=start_col_1,
                                     end_col=end_col_1,
                                     strand_col=strand_col_1,
                                     fix_strand=True )
    divide( interval, out_path )
    temp_file.close()
