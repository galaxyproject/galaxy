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
    pat_indel = re.compile( '(?P<before_match>(\d+[MIDNSHP])*)(?P<lmatch>\d+)M(?P<ins_del_width>\d+)(?P<ins_del>[ID])(?P<rmatch>\d+)M' )
    pat_matches = re.compile( '\d+[MIDNSHP]' )
    qual_thresh = int( options.quality_threshold )
    adj_bases = int( options.adjacent_bases )
    # go through all lines in input file
    for line in open( options.input, 'rb' ):
        if line and not line.startswith( '#' ) and not line.startswith( '@' ) :
            split_line = line.split( '\t' )
            cigar = split_line[5]
            # find all possible matches, like 3M2D7M and 7M3I10M in 3M2D7M3I10M
            cigar_copy = cigar[:]
            matches = []
            while len( cigar_copy ) >= 6:  # nMnInM or nMnDnM
                m = pat_indel.match( cigar_copy )
                if not m:
                    break
                else:
                    parts = m.groupdict()
                    parts[ 'start' ] = m.start()
                    matches.append( parts )
                    cigar_copy = cigar_copy[ len( parts[ 'lmatch' ] ) : ]
            # see if matches meet filter requirements
            if len( matches ) == 1:
                start = int( matches[0][ 'start' ] )
                left = int( matches[0][ 'lmatch' ] )
                right = int( matches[0][ 'rmatch' ] )
                if matches[0][ 'ins_del' ] == 'D':
                    middle = int( matches[0][ 'ins_del_width' ] )
                else:
                    middle = 0
                # if there are enough adjacent bases to check, then do so
                if left >= adj_bases and right >= adj_bases:
                    qual = split_line[10]
                    left_bases = qual[ start : start + left + 1 ][ -adj_bases : ]
                    right_bases = qual[ start + left + middle : start + left + middle + right + 1 ][ : adj_bases ]
                    qual_thresh_met = True
                    for l in left_bases:
                        if ord( l ) < qual_thresh:
                            qual_thresh_met = False
                            break
                    if qual_thresh_met:
                        for r in right_bases:
                            if ord( r ) < qual_thresh:
                                qual_thresh_met = False
                                break
                    # if filter reqs met, output line
                    if qual_thresh_met:
                        output.write( line )
            # error if there are multiple indels
            elif len( matches ) > 1:
                stop_err( 'There is more than one indel present in the alignment:\n%s' % line )
    # close out file
    output.close()

if __name__=="__main__": __main__()
