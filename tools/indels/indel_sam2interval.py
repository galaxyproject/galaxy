#!/usr/bin/env python

"""
Allows user to filter out non-indels from SAM.

usage: %prog [options]
   -i, --input=i: The input SAM file
   -u, --include_base=u: Whether or not to include the base for insertions
   -c, --collapse=c: Wheter to collapse multiple occurrences of a location with counts shown
   -o, --int_out=o: The interval output file for the converted SAM file
   -b, --bed_ins_out=b: The bed output file with insertions only for the converted SAM file
   -d, --bed_del_out=d: The bed output file with deletions only for the converted SAM file
"""

import re, sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse


def stop_err( msg ):
    sys.stderr.write( '%s\n' % msg )
    sys.exit()

def numeric_sort( text1, text2 ):
    """
    For two items containing space-separated text, compares equivalent pieces
    numerically if both numeric or as text otherwise
    """
    pieces1 = text1.split()
    pieces2 = text2.split()
    if len( pieces1 ) == 0:
        return 1
    if len( pieces2 ) == 0:
        return -1
    for i, pc1 in enumerate( pieces1 ):
        if i == len( pieces2 ):
            return 1
        if not pieces2[i].isdigit():
            if pc1.isdigit():
                return -1
            else:
                if pc1 > pieces2[i]:
                    return 1
                elif pc1 < pieces2[i]:
                    return -1
        else:
            if not pc1.isdigit():
                return 1
            else:
                if int( pc1 ) > int( pieces2[i] ):
                    return 1
                elif int( pc1 ) < int( pieces2[i] ):
                    return -1
    if i < len( pieces2 ) - 1:
        return -1
    return 0

def __main__():
    #Parse Command Line
    options, args = doc_optparse.parse( __doc__ )

    # open up output files
    output = open( options.int_out, 'wb' )
    if options.bed_ins_out != 'None':
        output_bed_ins = open( options.bed_ins_out, 'wb' )
    else:
        output_bed_ins = None
    if options.bed_del_out != 'None':
        output_bed_del = open( options.bed_del_out, 'wb' )
    else:
        output_bed_del = None

    # the pattern to match, assuming just one indel per cigar string
    pat_indel = re.compile( '^(?P<lmatch>\d+)M(?P<ins_del_width>\d+)(?P<ins_del>[ID])(?P<rmatch>\d+)M$' )
    pat_multi = re.compile( '(\d+[MIDNSHP])(\d+[MIDNSHP])(\d+[MIDNSHP])+' )

    # go through all lines in input file
    out_data = {}
    multi_indel_lines = 0
    for line in open( options.input, 'rb' ):
        if line and not line.startswith( '#' ) and not line.startswith( '@' ) :
            split_line = line.split( '\t' )
            if split_line < 12:
                continue
            # grab relevant pieces
            cigar = split_line[5].strip()
            pos = int( split_line[3] )
            chr = split_line[2]
            base_string = split_line[9]
            # parse cigar string
            m = pat_indel.match( cigar )
            if not m:
                m = pat_multi.match( cigar )
                # skip this line if no match
                if not m:
                    continue
                # account for multiple indels or operations we don't process
                else:
                    multi_indel_lines += 1
                continue
            else:
                match = m.groupdict()
            left = int( match[ 'lmatch' ] )
            middle = int( match[ 'ins_del_width' ] )
            middle_type = match[ 'ins_del' ]
            bases = base_string[ left : left + middle ]
            # calculate start and end positions, and output to insertion or deletion file
            start = left + pos
            if middle_type == 'D':
                end = start + middle
                data = [ chr, start, end, 'D' ]
                if options.include_base == "true":
                    data.append( '-' )
            else:
                end = start + 1
                data = [ chr, start, end, 'I' ]
                if options.include_base == "true":
                    data.append( bases )
            location = '\t'.join( [ '%s' % d for d in data ] )
            try:
                out_data[ location ] += 1
            except KeyError:
                out_data[ location ] = 1
    # output to interval file
    # get all locations and sort
    locations = out_data.keys()
    locations.sort( numeric_sort )
    last_line = ''
    # output each location, either with counts or each occurrence
    for loc in locations:
        sp_loc = loc.split( '\t' )
        cur_line = '\t'.join( sp_loc[:3] )
        if options.collapse == 'true':
            output.write( '%s\t%s\n' % ( loc, out_data[ loc ] ) )
            if output_bed_del and sp_loc[3] == 'D':
                output_bed_del.write( '%s\n' % cur_line )
            if output_bed_ins and sp_loc[3] == 'I' and last_line != cur_line:
                output_bed_ins.write( '%s\n' % cur_line )
                last_line = cur_line
        else:
            for i in range( out_data[ loc ] ):
                output.write( '%s\n' % loc )
                if output_bed_del or output_bed_ins:
                    if output_bed_del and sp_loc[3] == 'D':
                        output_bed_del.write( '%s\n' % cur_line )
                    if output_bed_ins and sp_loc[3] == 'I':
                        output_bed_ins.write( '%s\n' % cur_line )

    # cleanup, close files
    if output_bed_ins:
        output_bed_ins.close()
    if output_bed_del:
        output_bed_del.close()
    output.close()

    # if skipped lines because of more than one indel, output message
    if multi_indel_lines > 0:
        sys.stdout.write( '%s alignments were skipped because they contained more than one indel.' % multi_indel_lines )

if __name__=="__main__": __main__()
