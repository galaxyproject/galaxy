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
    pat_indel = re.compile( '(?P<before_match>(\d+[MNSHP])*)(?P<lmatch>\d+)M(?P<ins_del_width>\d+)(?P<ins_del>[ID])(?P<rmatch>\d+)M(?P<after_match>(\d+[MNSHP])*)' )
    pat_matches = re.compile( '(\d+[MIDNSHP])+' )
    try:
        qual_thresh = int( options.quality_threshold ) + 33
        if qual_thresh < 33 or qual_thresh > 126:
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
            cigar = split_line[5]
            # find all possible matches, like 3M2D7M and 7M3I10M in 3M2D7M3I10M
            cigar_copy = cigar[:]
            matches = []
            while len( cigar_copy ) >= 6:  # nMnInM or nMnDnM
                m = pat_indel.search( cigar_copy )
                if not m:
                    break
                else:
                    parts = m.groupdict()
                    if parts[ 'lmatch' ] and parts[ 'ins_del_width' ] and parts[ 'rmatch' ]:
                        pre_left = 0
                        if m.start() > 0:
                            pre_left_groups = pat_matches.search( cigar_copy[ : m.start() ] )
                            if pre_left_groups:
                                for pl in pre_left_groups.groups():
                                    if pl.endswith( 'M' ) or pl.endswith( 'S' ) or pl.endswith( 'P' ):
                                        pre_left += pl[:-1]
                        parts[ 'pre_left' ] = pre_left
                        matches.append( parts )
                    cigar_copy = cigar_copy[ len( parts[ 'lmatch' ] ) + 1 : ]
            # see if matches meet filter requirements
            if len( matches ) > 1:
                multi_indel_lines += 1
            elif len( matches ) == 1:
                pre_left = int( matches[0][ 'pre_left' ] )
                left = int( matches[0][ 'lmatch' ] )
                right = int( matches[0][ 'rmatch' ] )
                if matches[0][ 'ins_del' ] == 'D':
                    middle = int( matches[0][ 'ins_del_width' ] )
                else:
                    middle = 0
                # if there are enough adjacent bases to check, then do so
                if left >= adj_bases and right >= adj_bases:
                    quals = split_line[10]
                    left_quals = quals[ pre_left : pre_left + left ][ -adj_bases : ]
                    middle_quals = quals[ pre_left + left : pre_left + left + middle ]
                    right_quals = quals[ pre_left + left + middle : pre_left + left + middle + right ][ : adj_bases ]
                    qual_thresh_met = True
                    for l in left_quals:
                        if ord( l ) < qual_thresh:
                            qual_thresh_met = False
                            break
                    if qual_thresh_met:
                        for r in right_quals:
                            if ord( r ) < qual_thresh:
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
