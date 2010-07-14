#!/usr/bin/env python

"""
Given an input sam file, provides analysis of the indels..

usage: %prog [options] [input3 sum3[ input4 sum4[ input5 sum5[...]]]]
   -i, --input=i: The sam file to analyze
   -t, --threshold=t: The deletion frequency threshold
   -I, --out_ins=I: The interval output file showing insertions
   -D, --out_del=D: The interval output file showing deletions
"""

import re, sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse


def stop_err( msg ):
    sys.stderr.write( '%s\n' % msg )
    sys.exit()

def add_to_ref_pos( ref_pos, pos, bases ):
    """
    Adds the bases and counts to the ref_pos dict
    """
    for j, base in enumerate( bases ):
        try:
            ref_pos[ pos + j ][ base ] += 1
        except KeyError:
            try:
                ref_pos[ pos + j ][ base ] = 1
            except KeyError:
                ref_pos[ pos + j ] = { base: 1 }

def __main__():
    #Parse Command Line
    options, args = doc_optparse.parse( __doc__ )
    # prep output files
    out_ins = open( options.out_ins, 'wb' )
    out_del = open( options.out_del, 'wb' )
    # pattern
    pat = re.compile( '(^(?P<lmatch>\d+)M(?P<ins_del_width>\d+)(?P<ins_del>[ID])(?P<rmatch>\d+)M$)|(^(?P<match_width>\d+)M$)' )
    pat_multi = re.compile( '(\d+[MIDNSHP])(\d+[MIDNSHP])(\d+[MIDNSHP])+' )
    # for tracking occurences at each pos of ref
    ref_pos = {}
    indels = {}
    num_reads = {}
    multi_indel_lines = 0
    # go through all lines in input file
    for i,line in enumerate( open( options.input, 'rb' ) ):
        if line and not line.startswith( '#' ) and not line.startswith( '@' ) :
            split_line = line.split( '\t' )
            chrom = split_line[2].strip()
            pos = int( split_line[3].strip() )
            cigar = split_line[5].strip()
            bases = split_line[9].strip()
            # if not an indel or match, exit
            if chrom == '*':
                continue
            # find matches like 3M2D7M or 7M3I10M
            matches = ''
            m = pat.search( cigar )
            # unprocessable CIGAR
            if not m:
                m = pat_multi.search( cigar )
                # skip this line if no match
                if not m:
                    continue
                # account for multiple indels or operations we don't process
                else:
                    multi_indel_lines += 1
            # get matching parts for the indel or full match if matching
            else:
                if not ref_pos.has_key( chrom ):
                    ref_pos[ chrom ] = {}
                    indels[ chrom ] = { 'D': {}, 'I': {} }
                    if not num_reads.has_key( chrom ):
                        num_reads[ chrom ] = {}
                parts = m.groupdict()
                if parts[ 'match_width' ] or ( parts[ 'lmatch' ] and parts[ 'ins_del_width' ] and parts[ 'rmatch' ] ):
                    match = parts
            # see if matches meet filter requirements
            if match:
                # match/mismatch
                if parts[ 'match_width' ]:
                    add_to_ref_pos( ref_pos[ chrom ], pos, bases )
                    for i, base in enumerate( bases ):
                        try:
                            num_reads[ chrom ][ i + pos ] += 1
                        except KeyError:
                            num_reads[ chrom ][ i + pos ] = 1
                # indel
                else:
                    # pieces of CIGAR string
                    left = int( match[ 'lmatch' ] )
                    middle = int( match[ 'ins_del_width' ] )
                    right = int( match[ 'rmatch' ] )
                    left_bases = bases[ : left ]
                    if match[ 'ins_del' ] == 'I':
                        middle_bases = bases[ left : left + middle ]
                    else:
                        middle_bases = ''
                    right_bases = bases[ -right : ]
                    start = pos + left
                    # add data to ref_pos dict for match/mismatch bases on left and on right
                    add_to_ref_pos( ref_pos[ chrom ], pos, left_bases )
                    for i, base in enumerate( left_bases ):
                        try:
                            num_reads[ chrom ][ i + pos ] += 1
                        except KeyError:
                            num_reads[ chrom ][ i + pos ] = 1
                    if match[ 'ins_del' ] == 'I':
                        add_to_ref_pos( ref_pos[ chrom ], start, right_bases )
                        indel_pos = start
                    else:
                        add_to_ref_pos( ref_pos[ chrom ], start + middle, right_bases )
                        indel_pos = start + middle
                    for i, base in enumerate( right_bases ):
                        try:
                            num_reads[ chrom ][ i + indel_pos ] += 1
                        except KeyError:
                            num_reads[ chrom ][ i + indel_pos ] = 1
                    # for insertions, count instances of particular inserted bases
                    if match[ 'ins_del' ] == 'I':
                        if indels[ chrom ][ 'I' ].has_key( start ):
                            if indels[ chrom ][ 'I' ][ start ].has_key( middle_bases ):
                                indels[ chrom ][ 'I' ][ start ][ middle_bases ] += 1
                            else:
                                indels[ chrom ][ 'I' ][ start ][ middle_bases ] = 1
                        else:
                            indels[ chrom ][ 'I' ][ start ] = { middle_bases: 1 }
                    # for deletions, count number of deletions bases
                    else:
                        if indels[ chrom ][ 'D' ].has_key( start ):
                            if indels[ chrom ][ 'D' ][ start ].has_key( middle ):
                                indels[ chrom ][ 'D' ][ start ][ middle ] += 1
                            else:
                                indels[ chrom ][ 'D' ][ start ][ middle ] = 1
                        else:
                            indels[ chrom ][ 'D' ][ start ] = { middle: 1 }
    # compute deletion frequencies and insertion frequencies for checking against threshold
    freqs = {}
    ins_freqs = {}
    chroms = ref_pos.keys()
    chroms.sort()
    for chrom in chroms:
        freqs[ chrom ] = {}
        ins_freqs[ chrom ] = {}
        poses = num_reads[ chrom ].keys()
        poses.sort()
        for pos in poses:
            # all reads touching this particular position
            freqs[ chrom ][ pos ] = {}
            sum_counts = 0.0
            sum_counts_end = 0.0
            # get basic counts (match/mismatch)
            if num_reads[ chrom ].has_key( pos ):
                sum_counts += float( num_reads[ chrom ][ pos ] )
                try:
                    sum_counts_end += float( num_reads[ chrom ][ pos + 1 ] )
                except KeyError:
                    pass
            # add deletions also touching this position
            try:
                sum_counts += float( sum( indels[ chrom ][ 'D' ][ pos ].values() ) )
                try:
                    sum_counts_end += float( sum( indels[ chrom ][ 'D' ][ pos + 1 ].values() ) )
                except KeyError:
                    pass
                for d in indels[ chrom ][ 'D' ][ pos ].keys():
                    freqs[ chrom ][ pos ][ '-' * d ] = indels[ chrom ][ 'D' ][ pos ][ d ] / sum_counts
            except KeyError:
                pass
            # calculate actual frequencies
            # deletions
            freqs[ chrom ][ pos ][ 'total' ] = sum_counts
            for base in ref_pos[ chrom ][ pos ].keys():
                try:
                    prop = float( ref_pos[ chrom ][ pos ][ base ] ) / sum_counts
                    freqs[ chrom ][ pos ][ base ] = prop
                except ZeroDivisionError:
                    freqs[ chrom ][ pos ][ base ] = 0.0
            try:
                for d in indels[ chrom ][ 'D' ][ pos ].keys():
                    freqs[ chrom ][ pos ][ '-' * d ] = indels[ chrom ][ 'D' ][ pos ][ d ] / sum_counts
            except KeyError:
                pass
            # insertions
            try:
                for bases in indels[ chrom ][ 'I' ][ pos ].keys():
                    prop_start = indels[ chrom ][ 'I' ][ pos ][ bases ] / ( indels[ chrom ][ 'I' ][ pos ][ bases ] + sum_counts )
                    try:
                        prop_end = indels[ chrom ][ 'I' ][ pos ][ bases ] / sum_counts_end
                    except ZeroDivisionError:
                        prop_end = 0.0
                    try:
                        ins_freqs[ chrom ][ pos ][ bases ] = [ prop_start, prop_end ]
                    except KeyError:
                        ins_freqs[ chrom ][ pos ] = { bases: [ prop_start, prop_end ] }
            except KeyError, e:
                pass
    # output to files if meet threshold requirement
    threshold = float( options.threshold )
    #out_del.write( '#Chrom\tStart\tEnd\t#Del\t#Reads\t%TotReads\n' )
    #out_ins.write( '#Chrom\tStart\tEnd\tInsBases\t#Reads\t%TotReadsAtStart\t%ReadsAtEnd\n' )
    for chrom in ref_pos.keys():
        # deletions file
        poses = indels[ chrom ][ 'D' ].keys()
        poses.sort()
        for pos in poses:
            start = pos
            dels = indels[ chrom ][ 'D' ][ start ].keys()
            dels.sort()
            for d in dels:
                end = start + d
                prop = freqs[ chrom ][ start ][ '-' * d ]
                if prop > threshold :
                    out_del.write( '%s\t%s\t%s\t%s\t%s\t%.2f\n' % ( chrom, start, end, d, indels[ chrom ][ 'D' ][ pos ][ d ], 100.0 * prop ) )
        # insertions file
        poses = indels[ chrom ][ 'I' ].keys()
        poses.sort()
        for pos in poses:
            start = pos
            end = pos + 1
            ins_bases = indels[ chrom ][ 'I' ][ start ].keys()
            ins_bases.sort()
            for bases in ins_bases:
                prop_start = ins_freqs[ chrom ][ start ][ bases ][0]
                prop_end = ins_freqs[ chrom ][ start ][ bases ][1]
                if prop_start > threshold or prop_end > threshold:
                    out_ins.write( '%s\t%s\t%s\t%s\t%s\t%.2f\t%.2f\n' % ( chrom, start, end, bases, indels[ chrom ][ 'I' ][ start ][ bases ], 100.0 * prop_start, 100.0 * prop_end ) )
    # close out files
    out_del.close()
    out_ins.close()
    # if skipped lines because of more than one indel, output message
    if multi_indel_lines > 0:
        sys.stdout.write( '%s alignments were skipped because they contained more than one indel or had unhandled operations (N/S/H/P).' % multi_indel_lines )

if __name__=="__main__": __main__()
