#!/usr/bin/env python

"""
Combines several interval files containing indels with counts. All input files need to have the same number of columns.

usage: %prog [options] [input3 sum3[ input4 sum4[ input5 sum5[...]]]]
   -1, --input1=1: The first input file
   -s, --sum1=s: Whether or not to include the totals from first file in overall total
   -2, --input2=2: The second input file
   -S, --sum2=S: Whether or not to include the totals from second file in overall total
   -o, --output=o: The interval output file for the combined files
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
    # Parse Command Line
    options, args = doc_optparse.parse( __doc__ )
    inputs = [ options.input1, options.input2 ]
    includes = [ options.sum1, options.sum2 ]
    inputs.extend( [ a for i, a in enumerate( args ) if i % 2 == 0 ] )
    includes.extend( [ a for i, a in enumerate( args ) if i % 2 == 1 ] )
    num_cols = 0
    counts = {}
    # read in data from all files and get total counts
    try:
        for i, input in enumerate( inputs ):
            for line in open( input, 'rb' ):
                sp_line = line.strip().split( '\t' )
                # set num_cols on first pass
                if num_cols == 0:
                    if len( sp_line ) < 4:
                        raise Exception, 'There need to be at least 4 columns in the file: Chrom, Start, End, and Count'
                    num_cols = len( sp_line )
                # deal with differing number of columns
                elif len( sp_line ) != num_cols:
                    raise Exception, 'All of the files need to have the same number of columns (current %s != %s of first line)' % ( len( sp_line ), num_cols )
                # get actual counts for each indel
                indel = '\t'.join( sp_line[:-1] )
                try:
                    count = int( sp_line[-1] )
                except ValueError, e:
                    raise Exception, 'The last column of each file must be numeric, with the count of the number of instances of that indel: %s' % str( e )
                # total across all included files
                if includes[i] == "true":
                    try:
                        counts[ indel ]['tot'] += count
                    except ( IndexError, KeyError ):
                        counts[ indel ] = { 'tot': count }
                # counts for ith file
                counts[ indel ][i] = count
    except Exception, e:
        stop_err( 'Failed to read all input files:\n%s' % str( e ) )
    # output combined results to table file
    try:
        output = open( options.output, 'wb' )
        count_keys = counts.keys()
        count_keys.sort( numeric_sort )
        for indel in count_keys:
            count_out = [ str( counts[ indel ][ 'tot' ] ) ]
            for i in range( len( inputs ) ):
                try:
                    count_out.append( str( counts[ indel ][i] ) )
                except KeyError:
                    count_out.append( '0' )
            output.write( '%s\t%s\n' % ( indel, '\t'.join( count_out ) ) )
        output.close()
    except Exception, e:
        stop_err( 'Failed to output data: %s' % str( e ) )

if __name__=="__main__": __main__()
