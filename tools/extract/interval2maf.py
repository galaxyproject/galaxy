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
   -t, --mafType=t: Type of MAF source to use
   -i, --interval_file=i:       Input interval file
   -o, --output_file=o:      Output MAF file
"""

import psyco_full

import cookbook.doc_optparse

import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align.maf
from bx import misc
import os
import sys

def __main__():

    # Parse Command Line

    options, args = cookbook.doc_optparse.parse( __doc__ )
    
    # Going to leave a bunch of James's original functionality commented out in here, maybe add some back later.
    
    #dictionary of available maf files
    maf_sets = {}
    try:
        for line in open( "/cache/maf/maf_index.loc" ):
            if line[0:1] == "#" : continue
            fields = line.split('\t')
            #read each line, if not enough fields, go to next line
            try:
                maf_desc = fields[0]
                maf_uid = fields[1]
                builds = fields[2]
                build_to_common_list = {}
                common_to_build_list = {}
                split_builds = builds.split(",")
                for build in split_builds:
                    this_build = build.split("=")[0]
                    try:
                        this_common = build.split("=")[1]
                    except:
                        this_common = this_build
                    build_to_common_list[this_build]=this_common
                    common_to_build_list[this_common]=this_build
                    
                paths = fields[3].replace("\n","").replace("\r","")
                maf_sets[maf_uid]={}
                maf_sets[maf_uid]['description']=maf_desc
                maf_sets[maf_uid]['builds']=build_to_common_list
                maf_sets[maf_uid]['common']=common_to_build_list
                maf_sets[maf_uid]['paths']=paths.split(",")
            except:
                continue

    except Exception, exc:
        print >>sys.stdout, 'interval2maf.py initialization error -> %s' % exc 
    
    
    try:
        #maf_files = args
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
        
        if options.mafType: mafType= options.mafType
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
        
        
        #if options.src: fixed_src = options.src
        #else: fixed_src = None
        #if options.prefix: prefix = options.prefix
        #else: prefix = None
        #if options.dir: dir = options.dir
        #else: dir = None
        #chop = bool( options.chop )
        #do_strand = bool( options.strand )
    except:
        sys.exit()
        #cookbook.doc_optparse.exit()
        
    if dbkey == "?": 
        print >>sys.stderr, "You must specify a proper build in order to extract alignments."
        sys.exit()
    
    
    #Open MAF Files, with indexes
    try:
        maf_files = maf_sets[mafType]['paths']
    except:
        print >>sys.stderr, "The MAF source specified appears to be invalid."
        sys.exit()
    
    try:
        # Open indexed access to mafs
        index = bx.align.maf.MultiIndexed( maf_files )
    except:
        print >>sys.stderr, "The MAF source specified [", mafType ,"] appears to be missing."
        sys.exit()
    
    #convert dbkey to name in maf file, if no db->name entry, use build
    try:
        dbkey = maf_sets[mafType]['builds'][dbkey]
    except:
        print >>sys.stderr, "This MAF set is not available for this build."
        sys.exit()
    
    
    max_col_referenced = max([chromCol, startCol, endCol, strandCol])
    max_col_referenced_no_strand = max([chromCol, startCol, endCol])
    
    #if dir is None: 
    #    out = bx.align.maf.Writer( sys.stdout )
    output = open(output_file, "w");
    out = bx.align.maf.Writer( output )
    # Iterate over input ranges 
    num_blocks=0
    input = open(interval_file, "r")
    
    num_lines = 0
    for line in input.readlines():
        try:
            num_lines += 1
            if line[0:1]=="#":
                continue
            fields = line.split()
            strand_exists = True
            if len(fields) - 1 < max_col_referenced:
                strand_exists = False
            
            #if fixed_src:
            #    src, start, end = fixed_src, int( fields[0] ), int( fields[1] )
            #    if do_strand: strand = fields[2]
            #else:
            src, start, end = dbkey + "." + fields[chromCol], int( fields[startCol] ), int( fields[endCol] )
            if strandCol < 0 or not strand_exists:
                strand = "+"
            else:
                strand = fields[strandCol]
            
            #do a fix on src, chromosome for mlagan alignments (they lack chr)
            if mafType == "ENCODE_MLAGAN":
                src = src.replace(".chr",".")
            
            #if prefix: src = prefix + src
            # Find overlap with reference component
            blocks = index.get( src, start, end )
            # Open file if needed
            #if dir:
            #    out = bx.align.maf.Writer( open( os.path.join( dir, "%s:%09d-%09d.maf" % ( src, start, end ) ), 'w' ) )
            # Write each intersecting block
            #if chop:
            for block in blocks: 
                ref = block.get_component_by_src( src )
                #save old score here for later use
                old_score =  block.score
                # If the reference component is on the '-' strand we should complement the interval
                if ref.strand == '-':
                    slice_start = max( ref.src_size - end, ref.start )
                    slice_end = max( ref.src_size - start, ref.end )
                else:
                    slice_start = max( start, ref.start )
                    slice_end = min( end, ref.end )
                
                #when interval is out-of-range (not in maf index), fail silently: else could create tons of scroll
                try:
                    sliced = block.slice_by_component( ref, slice_start, slice_end ) 
                except:
                    continue
                    
                good = True
                for c in sliced.components: 
                    if c.size < 1: 
                        good = False
                if good and sliced.text_size > mincols:
                    if strand != ref.strand: sliced = sliced.reverse_complement()
                    # restore old score, may not be accurate, but it is better than 0 for everything
                    sliced.score = old_score
                    for c in sliced.components:
                        spec,chrom = bx.align.src_split( c.src )
                        if not spec or not chrom:
                            spec = chrom = c.src
                        if spec in maf_sets[mafType]['common']:
                            c.src = bx.align.src_merge(maf_sets[mafType]['common'][spec],chrom)
                    out.write( sliced )
                    num_blocks+=1
            #else:
            #    for block in blocks:
            #        out.write( block )
            #if dir:
            #    out.close()
        except:
            print "Error found on input line:",num_lines
            continue
    # Close output MAF

    out.close()
    print num_blocks, "MAF blocks extracted."
if __name__ == "__main__": __main__()
