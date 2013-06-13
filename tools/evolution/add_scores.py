#!/usr/bin/env python
from __future__ import with_statement

import sys
from galaxy import eggs
import pkg_resources
pkg_resources.require( "bx-python" )
pkg_resources.require( "numpy" )
from bx.bbi.bigwig_file import BigWigFile
import os

################################################################################

def die( message ):
    print >> sys.stderr, message
    sys.exit(1)

def open_or_die( filename, mode='r', message=None ):
    if message is None:
        message = 'Error opening %s' % filename
    try:
        fh = open( filename, mode )
    except IOError, err:
        die( '%s: %s' % ( message, err.strerror ) )
    return fh

################################################################################

class LocationFile( object ):
    def __init__( self, filename, comment_chars=None, delimiter='\t', key_column=0 ):
        self.filename = filename
        if comment_chars is None:
            self.comment_chars = ( '#' )
        else:
            self.comment_chars = tuple( comment_chars )
        self.delimiter = delimiter
        self.key_column = key_column
        self._map = {}
        self._populate_map()

    def _populate_map( self ):
        try:
            with open( self.filename ) as fh:
                line_number = 0
                for line in fh:
                    line_number += 1
                    line = line.rstrip( '\r\n' )
                    if not line.startswith( self.comment_chars ):
                        elems = line.split( self.delimiter )
                        if len( elems ) <= self.key_column:
                            die( 'Location file %s line %d: less than %d columns' % ( self.filename, line_number, self.key_column + 1 ) )
                        else:
                            key = elems.pop( self.key_column )
                            if key in self._map:
                                if self._map[key] != elems:
                                    die( 'Location file %s line %d: duplicate key "%s"' % ( self.filename, line_number, key ) )
                            else:
                                self._map[key] = elems
        except IOError, err:
            die( 'Error opening location file %s: %s' % ( self.filename, err.strerror ) )

    def get_values( self, key ):
        if key in self._map:
            rval = self._map[key]
            if len( rval ) == 1:
                return rval[0]
            else:
                return rval
        else:
            die( 'key "%s" not found in location file %s' % ( key, self.filename ) )

################################################################################

def main():
    input_filename, output_filename, loc_filename, loc_key, chrom_col, start_col = sys.argv[1:]

    # open input, output, and bigwig files
    location_file = LocationFile( loc_filename )
    bigwig_filename = location_file.get_values( loc_key )
    bwfh = open_or_die( bigwig_filename, message='Error opening BigWig file %s' % bigwig_filename )
    bw = BigWigFile( file=bwfh )
    ifh = open_or_die( input_filename, message='Error opening input file %s' % input_filename )
    ofh = open_or_die( output_filename, mode='w', message='Error opening output file %s' % output_filename )

    # make column numbers 0-based
    chrom_col = int( chrom_col ) - 1
    start_col = int( start_col ) - 1
    min_cols = max( chrom_col, start_col )

    # add score column to imput file
    line_number = 0
    for line in ifh:
        line_number += 1
        line = line.rstrip( '\r\n' )
        elems = line.split( '\t' )
        if len( elems ) > min_cols:
            chrom = elems[chrom_col].strip()
            # base-0 position in chrom
            start = int( elems[start_col] )
            score_list = bw.get( chrom, start, start + 1 )
            score_list_len = len( score_list )
            if score_list_len == 1:
                beg, end, score = score_list[0]
                score_val = '%1.3f' % score
            elif score_list_len == 0:
                score_val = 'NA'
            else:
                die( '%s line %d: chrom=%s, start=%d, score_list_len = %d' % ( input_filename, line_number, chrom, start, score_list_len ) )
            print >> ofh, '\t'.join( [line, score_val] )
        else:
            print >> ofh, line

    bwfh.close()
    ifh.close()
    ofh.close()

################################################################################

if __name__ == "__main__":
    main()

