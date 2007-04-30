#!/usr/bin/env python2.4
# Greg Von Kuster
"""
usage: %prog score_file interval_file chrom start stop [out_file] [options] 
    -b, --binned: 'score_file' is actually a directory of binned array files
    -m, --mask=FILE: bed file containing regions not to consider valid
"""

from __future__ import division
import pkg_resources 
pkg_resources.require( "bx-python" )
pkg_resources.require( "lrucache" )
try:
    pkg_resources.require( "python-lzo" )
except:
    pass

import psyco_full
import sys
import os, os.path
from UserDict import DictMixin
import bx.wiggle
from bx.binned_array import BinnedArray, FileBinnedArray
from bx.bitset import *
from bx.bitset_builders import *
from fpconst import isNaN
import cookbook.doc_optparse

class FileBinnedArrayDir( DictMixin ):
    """
    Adapter that makes a directory of FileBinnedArray files look like
    a regular dict of BinnedArray objects. 
    """
    def __init__( self, dir ):
        self.dir = dir
        self.cache = dict()
    def __getitem__( self, key ):
        value = None
        if key in self.cache:
            value = self.cache[key]
        else:
            fname = os.path.join( self.dir, "%s.ba" % key )
            if os.path.exists( fname ):
                value = FileBinnedArray( open( fname ) )
                self.cache[key] = value
        if value is None:
            raise KeyError( "File does not exist: " + fname )
        return value

"""
TODO: move the following 2 classes  to a better location so that other tools can take advantage of them.
Talk to Ian about possibly moving them to the bx egg.
"""
class UCSCLimitException( Exception ):
    pass

class UCSCOutWrapper( object ):
    """
    File-like object that throws an exception if it encounters the UCSC limit error lines
    """
    def __init__( self, other ):
        self.other = iter( other )
        # Need one line of lookahead to be sure we are hitting the limit message
        self.lookahead = None
    def __iter__( self ):
        return self
    def __next__( self ):
        if self.lookahead is None:
            line = self.other.next()
        else:
            line = self.lookahead
            self.lookahead = None
        if line.startswith( "----------" ):
            next_line = self.other.next()
            if next_line.startswith( "Reached output limit" ):
                raise UCSCLimitException( next_line.strip() )
            else:
                self.lookahead = next_line
        return line 
    def readline(self):
        # This function should only be called if the UCSC output limit is encountered.
        raise UCSCLimitException

def load_scores_wiggle( fname ):
    """
    Read a wiggle file and return a dict of BinnedArray objects keyed 
    by chromosome.
    """ 
    scores_by_chrom = dict()
    try:
        for chrom, pos, val in bx.wiggle.Reader( UCSCOutWrapper(open( fname ) ) ):
            if chrom not in scores_by_chrom:
                scores_by_chrom[chrom] = BinnedArray()
                scores_by_chrom[chrom][pos] = val
    except UCSCLimitException:
        # Wiggle data was truncated, at the very least need to warn the user.
        print 'Encountered message from UCSC: "Reached output limit of 100000 data values", so be aware your data was truncated.'
    return scores_by_chrom

def load_scores_ba_dir( dir ):
    """
    Return a dict-like object (keyed by chromosome) that returns 
    FileBinnedArray objects created from "key.ba" files in `dir`
    """
    return FileBinnedArrayDir( dir )
    
def main():

    # Parse command line
    options, args = cookbook.doc_optparse.parse( __doc__ )

    try:
        score_fname = args[0]
        interval_fname = args[1]
        chrom_col = args[2]
        start_col = args[3]
        stop_col = args[4]
        if len( args ) > 5:
            out_file = open( args[5], 'w' )
        else:
            out_file = sys.stdout
        binned = bool( options.binned )
        mask_fname = options.mask
    except:
        cookbook.doc_optparse.exit()

    if score_fname == 'None':
        print 'Invalid genome build - this tool currently only works with data from genome builds hg16, hg17 or hg18.  Click "edit attributes" (the pencil icon) in your history item to correct the genome build if appropriate.'
        sys.exit()
    
    try:
        chrom_col = int(chrom_col) - 1
        start_col = int(start_col) - 1
        stop_col = int(stop_col) - 1
    except:
        print 'Invalid column number for chrom, start or end column, chrom: %s start: %s end: %s' %(chrom_col, start_col, stop_col)
        sys.exit()

    if chrom_col < 0 or start_col < 0 or stop_col < 0:
        print 'Invalid column number for chrom, start or end column, chrom: %s start: %s end: %s' %(chrom_col, start_col, stop_col)
        sys.exit()
        
    if binned:
        scores_by_chrom = load_scores_ba_dir( score_fname )
    else:
        scores_by_chrom = load_scores_wiggle( score_fname )

    if mask_fname:
        masks = binned_bitsets_from_file( open( mask_fname ) )
    else:
        masks = None

    skipped_lines = 0
    first_invalid_line = 0
    invalid_line = None

    for i, line in enumerate( open( interval_fname )):
        line = line.strip()
        if line and line != '' and not line.startswith( '#' ):
            fields = line.split()
            
            try:
                chrom, start, stop = fields[chrom_col], int( fields[start_col] ), int( fields[stop_col] )                
                total = 0
                count = 0
                min_score = 100000000
                max_score = -100000000
                for j in range( start, stop ):
                    if chrom in scores_by_chrom and scores_by_chrom[chrom][j]:
                        # Skip if base is masked
                        if masks and chrom in masks:
                            if masks[chrom][j]:
                                continue
                        # Get the score, only count if not 'nan'
                        score = scores_by_chrom[chrom][j]
                        if not isNaN( score ):
                            total += score
                            count += 1
                            max_score = max( score, max_score )
                            min_score = min( score, min_score )
                if count > 0:
                    avg = total/count
                else:
                    avg = "nan"
                    min_score = "nan"
                    max_score = "nan"
                
                # Build the resulting line of data
                out_line = []
                for k in range(0, len(fields)):
                    out_line.append(fields[k])
                out_line.append(avg)
                out_line.append(min_score)
                out_line.append(max_score)
                
                print >> out_file, "\t".join( map( str, out_line ) )
            except:
                skipped_lines += 1
                if not invalid_line:
                    first_invalid_line = i + 1
                    invalid_line = line
        elif line.startswith( '#' ):
            # We'll save the original comments
            print >> out_file, line
            
    out_file.close()

    if skipped_lines > 0:
        print 'Data issue: skipped %d invalid lines starting at line #%d which is "%s"' % ( skipped_lines, first_invalid_line, invalid_line )
        if skipped_lines == i:
            print 'Consider changing the metadata for the input dataset by clicking on the pencil icon in the history item.'

if __name__ == "__main__": main()
