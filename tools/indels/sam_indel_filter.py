#!/usr/bin/env python

"""
Allows user to filter out non-indels from SAM.

usage: %prog [options]
   -i, --input=i: Input SAM file to be filtered
   -q, --quality_threshold=q: Minimum quality value for adjacent bases
   -a, --adjacent_bases=a: Number of adjacent bases on each size to check qualities
   -o, --output=o: Filtered output SAM file
"""

import re, sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse


def stop_err( msg ):
    sys.stderr.write( '%s\n' % msg )
    sys.exit()

def __main__():
    #Parse Command Line
    options, args = doc_optparse.parse( __doc__ )
    # prep output file
    output = open( options.output, 'wb' )
    # patterns
    pat = re.compile( '^(?P<lmatch>\d+)M(?P<ins_del_width>\d+)(?P<ins_del>[ID])(?P<rmatch>\d+)M$' )
    pat_multi = re.compile( '(\d+[MIDNSHP])(\d+[MIDNSHP])(\d+[MIDNSHP])+' )
    try:
        qual_thresh = int( options.quality_threshold )
        if qual_thresh < 0 or qual_thresh > 93:
            raise ValueError
    except ValueError:
        stop_err( 'Your quality threshold should be an integer between 0 and 93, inclusive.' )
    try:
        adj_bases = int( options.adjacent_bases )
        if adj_bases < 1:
            raise ValueError
    except ValueError:
        stop_err( 'The number of adjacent bases should be an integer greater than 1.' )
    # record lines skipped because of more than one indel
    multi_indel_lines = 0
    # go through all lines in input file
    for i,line in enumerate(open( options.input, 'rb' )):
        if line and not line.startswith( '#' ) and not line.startswith( '@' ) :
            split_line = line.split( '\t' )
            cigar = split_line[5].strip()
            # find matches like 3M2D7M or 7M3I10M
            match = {}
            m = pat.match( cigar )
            # if unprocessable CIGAR
            if not m:
                m = pat_multi.match( cigar )
                # skip this line if no match
                if not m:
                    continue
                # account for multiple indels or operations we don't process
                else:
                    multi_indel_lines += 1
            # otherwise get matching parts
            else:
                match = m.groupdict()
            # process for indels
            if match:
                left = int( match[ 'lmatch' ] )
                right = int( match[ 'rmatch' ] )
                if match[ 'ins_del' ] == 'I':
                    middle = int( match[ 'ins_del_width' ] )
                else:
                    middle = 0
                # if there are enough adjacent bases to check, then do so
                if left >= adj_bases and right >= adj_bases:
                    quals = split_line[10]
                    eligible_quals = quals[ left - adj_bases : left + middle + adj_bases ]
                    qual_thresh_met = True
                    for q in eligible_quals:
                        if ord( q ) - 33 < qual_thresh:
                            qual_thresh_met = False
                            break
                    # if filter reqs met, output line
                    if qual_thresh_met:
                        output.write( line )
    # close out file
    output.close()
    # if skipped lines because of more than one indel, output message
    if multi_indel_lines > 0:
        sys.stdout.write( '%s alignments were skipped because they contained more than one indel.' % multi_indel_lines )

if __name__=="__main__": __main__()
