#!/usr/bin/env python

"""
usage: %prog interval_file data1[,data2,] [options] 
-o, --outfile=OUTFILE: output file
-I, --included: print built-ins and quit
-S, --search=SEARCHPATH: prepend SEARCHPATH to default list
"""

from __future__ import division

import pkg_resources 
pkg_resources.require( "bx-python" )
pkg_resources.require( "lrucache" )
try:
    pkg_resources.require( "python-lzo" )
except:
    pass

import sys
import psyco_full
import bx.wiggle
from bx.binned_array import BinnedArray, FileBinnedArray
from bx import intervals
from fpconst import isNaN
import cookbook.doc_optparse
import misc
import os

from Numeric import *

def read_scores( f ):
    scores_by_chrom = dict()
    for chrom, pos, val in bx.wiggle.Reader( f ):
        if chrom not in scores_by_chrom:
            scores_by_chrom[chrom] = BinnedArray()
        scores_by_chrom[chrom][pos] = val
    return scores_by_chrom

# FIXME: Handle different builds better
DATA_SEARCH_PATH=['/cache/universe/binned_scores','.']
#DATA_SEARCH_PATH=['.']

class DataSet( object ):

    def __init__(self,datadir=None):
        self.lookup = None
        self.scores = None
        if not datadir == None:
            self.read_dir( datadir )

    def read_dir(self,  d):
        lookup = dict()
        scores_by_what = dict()
        if not os.path.exists ( d ):
            for p in DATA_SEARCH_PATH:
                if os.path.exists( os.path.join( p, d )):
                    d = os.path.join( p, d)
                    break
        for file in os.listdir( d ):
            if file.endswith(".match"):
                for line in (open( os.path.join( d, file))):
                    if line.startswith("#"): continue
                    line = line.strip()
                    f = line.split()
                    if len(f) >= 4:
                        chr,start,end,what = f[0:4]
                    else: continue

                    if not chr in lookup: lookup[chr] = intervals.Intersecter()
                    lookup[chr].add_interval( intervals.Interval( int( start), int( end ), what) )
            else:
                k = file.split('.')[0]
                if not k in scores_by_what: 
                    scores_by_what[ k ] = FileBinnedArray( open( os.path.join( d, file) ))

        if lookup == {}:
            self.lookup = None
            self.scores = scores_by_what
            #return None, scores_by_what
        else:
            self.lookup = lookup
            self.scores = scores_by_what
            #return lookup,scores_by_what

def main():

    # Parse command line
    options, args = cookbook.doc_optparse.parse( __doc__ )
    try:
        # add searchpath
        if options.search: 
            lr = options.search.split(",")
            lr.reverse()
            for x in lr:
                DATA_SEARCH_PATH.insert( 0, x)

        # print visible paths in the builtin directories
        if options.included:
            for p in DATA_SEARCH_PATH:
                if p == '.': continue
                for q in os.listdir( p ):
                    if os.path.isdir( os.path.join(p,q) ): 
                        if not q.startswith("."): 
                            print "\t\t",q
            raise "clean"
        elif options.outfile:
            out_file = open(options.outfile,"w")
        else:
            out_file = sys.stdout

        interval_file = open( args[0] )
    except "clean":
        sys.exit(0)
    except IOError,s:
        print >>sys.stderr,s
        cookbook.doc_optparse.exit()
    except:
        cookbook.doc_optparse.exit()
    

    datasets = []
    for i,datadir in enumerate( args[1].split(",") ):

        try:
            datasets.append( DataSet( datadir ) )
        except OSError,s:
            print >>sys.stderr, "skipped %s -- not in search path" % datadir

    for line in open( sys.argv[1] ):
        fields = line.split()
        try:
            chrom, start, stop = fields[0], int( fields[1] ), int( fields[2] )
        except ValueError,s:
            print >>sys.stderr, "skipping %s: %s" % (line,s)
            continue

        output = line.strip()
        for dataset in datasets:
            lookup = dataset.lookup
            scores_by_what = dataset.scores

            total = 0
            count = 0
            min_score = 100000000
            max_score = -100000000

            # if there was a regions.match file, 
            # map chromosome interval into the region
            if lookup != None:
                if chrom in lookup:
                    region = lookup[chrom].find( start, stop)
                    if region == []: what = ""
                    elif len(region) != 1:
                        print >>sys.stderr, "%s maps to more than one region" % (line)
                        raise ValueError
                    else: what = region[0].value
                else: what = chrom
            else: what = chrom
    
            if what in scores_by_what:
                # Get all scores in the range
                scores_in_range = scores_by_what[what][start:stop]
                # Ensure it is a Numeric array (this should be a noop)
                scores_in_range = array( scores_in_range )
                # Determine indexes that are 'nan'
                is_real = logical_not( scores_in_range != scores_in_range )
                # Extract just the real values
                real_scores = compress( is_real, scores_in_range )
                # Compute aggregates
                count = sum( is_real )
                if count > 0:
                    total = sum( real_scores.astype( Float64 ) )
                    avg = total / count
                    min_score = min( real_scores )
                    max_score = max( real_scores )
                else:
                    total = avg = min_score = max_score = float( "nan" )
            
            output = "\t".join([ output, "%.6f\t%.6f\t%.6f\t%.6f\t%d" % ( avg, min_score, max_score, total or float("nan"), count) ])
        print >> out_file,output

    interval_file.close()
    out_file.close()

if __name__ == "__main__": main()
