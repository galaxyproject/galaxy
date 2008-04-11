#!/usr/bin/env python

"""
usage: %prog data_file.h5 region_mapping.bed in_file out_file chrom_col start_col end_col [options]
   -p, --perCol: standardize to lod per column
"""

from __future__ import division

import sys
from galaxy import eggs
from numpy import *
from tables import *

import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse

from bx import intervals

# ignore wanrnings about NumArray flavor
from warnings import filterwarnings
from tables.exceptions import FlavorWarning
filterwarnings("ignore", category=FlavorWarning)

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write(msg)
    sys.exit()

def main():
    # Parse command line
    options, args = doc_optparse.parse( __doc__ )
    try:
        h5_fname = args[0]
        mapping_fname = args[1]
        in_fname = args[2]
        out_fname = args[3]
        chrom_col, start_col, end_col = map( lambda x: int( x ) - 1, args[4:7] )
        per_col = bool( options.perCol )
    except Exception, e:
        doc_optparse.exception()
        
    if h5_fname == 'None.h5':
        stop_err( 'Invalid genome build, this tool currently only works with data from build hg17.  Click the pencil icon in your history item to correct the build if appropriate.' )
        
    # Open the h5 file
    h5 = openFile( h5_fname, mode = "r" )
    # Load intervals and names for the subregions
    intersecters = {}
    for i, line in enumerate( file( mapping_fname ) ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ):
            chr, start, end, name = line.split()[0:4]
            if not intersecters.has_key( chr ): 
                intersecters[ chr ] = intervals.Intersecter()
            intersecters[ chr ].add_interval( intervals.Interval( int( start ), int( end ), name ) )

    # Find the subregion containing each input interval
    skipped_lines = 0
    first_invalid_line = 0
    invalid_line = ''
    out_file = open( out_fname, "w" )
    warnings = []
    warning = ''
    for i, line in enumerate( file( in_fname ) ):
        line = line.rstrip( '\r\n' )
        if line.startswith( '#' ):
            if i == 0:
                out_file.write( "%s\tscore\n" % line )
            else:
                out_file.write( "%s\n" % line )
        fields = line.split( "\t" )
        try:
            chr = fields[ chrom_col ]
            start = int( fields[ start_col ] )
            end = int( fields[ end_col ] )
        except:
            warning = "Invalid value for chrom, start or end column."
            warnings.append( warning )
            skipped_lines += 1
            if not invalid_line:
                first_invalid_line = i + 1
                invalid_line = line
            continue
        # Find matching interval
        try:
            matches = intersecters[ chr ].find( start, end )
        except:
            warning = "'%s' is not a valid chrom value for the region. " %chr
            warnings.append( warning )
            skipped_lines += 1
            if not invalid_line:
                first_invalid_line = i + 1
                invalid_line = line
            continue
        if not len( matches ) == 1:
            warning = "Interval must match exactly one target region. "
            warnings.append( warning )
            skipped_lines += 1
            if not invalid_line:
                first_invalid_line = i + 1
                invalid_line = line
            continue
        region = matches[0]
        if not ( start >= region.start and end <= region.end ):
            warning = "Interval must fall entirely within region. "
            warnings.append( warning )
            skipped_lines += 1
            if not invalid_line:
                first_invalid_line = i + 1
                invalid_line = line
            continue
        region_name = region.value
        rel_start = start - region.start
        rel_end = end - region.start
        if not rel_start < rel_end:
            warning = "Region %s is empty, relative start:%d, relative end:%d. " % ( region_name, rel_start, rel_end )
            warnings.append( warning )
            skipped_lines += 1
            if not invalid_line:
                first_invalid_line = i + 1
                invalid_line = line
            continue
        s = h5.getNode( h5.root, "scores_" + region_name )
        c = h5.getNode( h5.root, "counts_" + region_name )
        score = s[rel_end-1]
        count = c[rel_end-1]
        if rel_start > 0:
            score -= s[rel_start-1]
            count -= c[rel_start-1]
        if per_col: 
            score /= count
        fields.append( str( score ) )
        out_file.write( "%s\n" % "\t".join( fields ) )
    # Close the file handle
    h5.close()
    out_file.close()

    if warnings:
        warn_msg = "PhastOdds scores are only available for ENCODE regions. %d warnings, 1st is: " % len( warnings )
        warn_msg += warnings[0]
        print warn_msg
    if skipped_lines:
        print 'Skipped %d invalid lines, 1st is #%d, "%s"' % ( skipped_lines, first_invalid_line, invalid_line )

if __name__ == "__main__": main()
