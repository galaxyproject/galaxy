#!/usr/bin/env python2.3

"""
Reads a list of intervals and a maf. Produces a new maf containing the
blocks or parts of blocks in the original that overlapped the intervals.

If index_file is not provided maf_file.index is used.

NOTE: If two intervals overlap the same block it will be written twice. With
      non-overlapping intervals and --chop this is never a problem. - Chop has been made always on.

usage: %prog maf_file index_file [options] < interval_file
   -d, --dbkey=d: Database key, ie hg17
   -c, --chromCol=c: Column of Chr
   -s, --startCol=s: Column of Start
   -e, --endCol=e: Column of End
   -S, --strandCol=S: Column of Strand
   -m, --mafFile=m: MAF file source to use
   -i, --interval_file=i:       Input interval file
   -o, --output_file=o:      Output MAF file
"""

#import psyco_full

import cookbook.doc_optparse

import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align.maf
from bx import misc
import os
import sys

def __main__():

    # Parse Command Line

    options, args = cookbook.doc_optparse.parse( __doc__ )
    
    try:
        mincols=0
        
        if options.dbkey: dbkey = options.dbkey
        else: dbkey="?"
        
        
        if options.chromCol: chromCol= int(options.chromCol) - 1
        else: 
            print >>sys.stderr, "Chromosome column has not been specified."
            sys.exit()
        
        if options.startCol: startCol= int(options.startCol) - 1
        else: 
            print >>sys.stderr, "Start column has not been specified."
            sys.exit()
        
        if options.endCol: endCol= int(options.endCol) - 1
        else: 
            print >>sys.stderr, "End column has not been specified."
            sys.exit()
        
        if options.strandCol: strandCol= int(options.strandCol) - 1
        else: 
            print >>sys.stderr, "Strand column has not been specified."
            sys.exit()
        
        if options.mafFile: mafFile= options.mafFile
        else: 
            print >>sys.stderr, "Desired source MAF type has not been specified."
            sys.exit()
        
        if options.interval_file: interval_file= options.interval_file
        else: 
            print >>sys.stderr, "Input interval file has not been specified."
            sys.exit()
        
        if options.output_file: output_file= options.output_file
        else: 
            print >>sys.stderr, "Output file has not been specified."
            sys.exit()
    except:
        sys.exit()
                
    if dbkey == "?": 
        print >>sys.stderr, "You must specify a proper build in order to extract alignments."
        sys.exit()
    
    
    max_col_referenced = max([chromCol, startCol, endCol, strandCol])
    max_col_referenced_no_strand = max([chromCol, startCol, endCol])
    
    output = open(output_file, "w");
    out = bx.align.maf.Writer( output )
    
    # Iterate over input ranges 
    num_blocks=0
    
    try:
        for maf in bx.align.maf.Reader(open(mafFile, "r")):
            try:
                for line in open(interval_file, "r").readlines():
                    try:
                        if line[0:1]=="#":
                            continue
                        fields = line.split()
                        strand_exists = True
                        if len(fields) - 1 < max_col_referenced:
                            strand_exists = False
                        
                        src, start, end = dbkey + "." + fields[chromCol], int( fields[startCol] ), int( fields[endCol] )
                        if strandCol < 0 or not strand_exists:
                            strand = "+"
                        else:
                            strand = fields[strandCol]
                        ref = maf.get_component_by_src( src )
                        
                        #save old score here for later use
                        old_score =  maf.score
                        # If the reference component is on the '-' strand we should complement the interval
                        if ref.strand == '-':
                            slice_start = max( ref.src_size - end, ref.start )
                            slice_end = max( ref.src_size - start, ref.end )
                        else:
                            slice_start = max( start, ref.start )
                            slice_end = min( end, ref.end )
                        
                        #when interval is out-of-range (not in maf index), fail silently: else could create tons of scroll
                        try:
                            sliced = maf.slice_by_component( ref, slice_start, slice_end ) 
                        except:
                            continue
                            
                        good = True
                        #for c in sliced.components: 
                        #    if c.size < 1: 
                        #        good = False
                        if good and sliced.text_size > mincols:
                            if strand != ref.strand: sliced = sliced.reverse_complement()
                            # restore old score, may not be accurate, but it is better than 0 for everything
                            sliced.score = old_score
                            out.write( sliced )
                            num_blocks+=1
                    except:
                        continue
            except:
                print "Error Reading Interval File."
        # Close output MAF
        out.close()
        print num_blocks, "MAF blocks extracted."
    except:
        print "Error Reading MAF File"
    
if __name__ == "__main__": __main__()
