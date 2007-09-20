#!/usr/bin/env python2.4

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

#import psyco_full

import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse

import bx.align.maf
from bx import interval_index_file
import bx.intervals.io
from bx import misc
import os
import sys

def __main__():

    # Parse Command Line

    options, args = doc_optparse.parse( __doc__ )
    
    
    #dictionary of available maf files
    maf_sets = {}
    try:
        for line in open( "/depot/data2/galaxy/maf_index.loc" ):
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
        
    except:
        sys.exit()
        
    if dbkey == "?": 
        print >>sys.stderr, "You must specify a proper build in order to extract alignments. You can specify your genome build by clicking on the pencil icon associated with your interval file."
        sys.exit()
    
    
    #Open MAF Files, with indexes
    try:
        maf_files = maf_sets[mafType]['paths']
    except:
        print >>sys.stderr, "The MAF source specified appears to be invalid."
        sys.exit()
    
    try:
        # Open indexed access to mafs
        index = bx.align.maf.MultiIndexed( maf_files, keep_open=True, parse_e_rows=True )
    except:
        print >>sys.stderr, "The MAF source specified [", mafType ,"] appears to be missing."
        sys.exit()
    
    #convert dbkey to name in maf file, if no db->name entry, use build
    try:
        dbkey = maf_sets[mafType]['builds'][dbkey]
    except:
        print >>sys.stderr, "This MAF set is not available for this build."
        sys.exit()
    
    out = bx.align.maf.Writer( open(output_file, "w") )
    
    # Iterate over input ranges 
    num_blocks=0
    num_lines = 0
    for region in bx.intervals.io.NiceReaderWrapper( open(interval_file, 'r' ), chrom_col=chromCol, start_col=startCol, end_col=endCol, strand_col=strandCol, fix_strand=True, return_header=False, return_comments=False):
        try:
            num_lines += 1
            src = "%s.%s" % (dbkey,region.chrom)
            start = region.start
            end = region.end
            strand = region.strand

            #do a fix on src, chromosome for mlagan alignments (they lack chr)
            if mafType == "ENCODE_MLAGAN":
                src = src.replace(".chr",".")
            
            blocks = index.get( src, start, end )
            for block in blocks: 
                ref = block.get_component_by_src( src )
                #We want our block coordinates to be from positive strand
                if ref.strand == "-":
                    block = block.reverse_complement()
                    ref = block.get_component_by_src( src )
                
                #save old score here for later use
                old_score =  block.score
                slice_start = max( start, ref.start )
                slice_end = min( end, ref.end )
                
                #when interval is out-of-range (not in maf index), fail silently: else could create tons of scroll
                try:
                    sliced = block.slice_by_component( ref, slice_start, slice_end ) 
                except:
                    continue
                    
                if sliced.text_size > mincols:
                    if strand != ref.strand: sliced = sliced.reverse_complement()
                    # restore old score, may not be accurate, but it is better than 0 for everything
                    sliced.score = old_score
                    for c in sliced.components:
                        spec,chrom = bx.align.src_split( c.src )
                        if not spec or not chrom:
                            spec = chrom = c.src
                            c.src = bx.align.src_merge(spec,chrom)
                        if spec in maf_sets[mafType]['common']:
                            c.src = bx.align.src_merge(maf_sets[mafType]['common'][spec],chrom)
                    out.write( sliced )
                    num_blocks+=1
        except Exception, e:
            print "Error found on input line:",num_lines
            print e
            continue
    
    # Close output MAF
    out.close()
    print num_blocks, "MAF blocks extracted."
if __name__ == "__main__": __main__()
