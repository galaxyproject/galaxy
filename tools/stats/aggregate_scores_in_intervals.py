#!/usr/bin/env python2.4

"""
usage: %prog score_file interval_file [out_file] [options] 
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

def load_scores_wiggle( fname ):
    """
    Read a wiggle file and return a dict of BinnedArray objects keyed 
    by chromosome.
    """
    scores_by_chrom = dict()
    for chrom, pos, val in bx.wiggle.Reader( open( fname ) ):
        if chrom not in scores_by_chrom:
            scores_by_chrom[chrom] = BinnedArray()
        scores_by_chrom[chrom][pos] = val
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
        if len( args ) > 2:
            out_file = open( args[2], 'w' )
        else:
            out_file = sys.stdout
        binned = bool( options.binned )
        mask_fname = options.mask
    except:
        cookbook.doc_optparse.exit()

    if binned:
        scores_by_chrom = load_scores_ba_dir( score_fname )
    else:
        scores_by_chrom = load_scores_wiggle( score_fname )

    if mask_fname:
        masks = binned_bitsets_from_file( open( mask_fname ) )
    else:
        masks = None

    for line in open( interval_fname ):
        fields = line.split()
        chrom, start, stop = fields[0], int( fields[1] ), int( fields[2] )
        total = 0
        count = 0
        min_score = 100000000
        max_score = -100000000
        for i in range( start, stop ):
            if chrom in scores_by_chrom and scores_by_chrom[chrom][i]:
                # Skip if base is masked
                if masks and chrom in masks:
                    if masks[chrom][i]:
                        continue
                # Get the score, only count if not 'nan'
                score = scores_by_chrom[chrom][i]
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
            
        print >> out_file, "\t".join( map( str, [ chrom, start, stop, avg, min_score, max_score ] ) )

    out_file.close()

if __name__ == "__main__": main()
