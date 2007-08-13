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
   -m, --mafFile=m: MAF file source to use
   -i, --interval_file=i:       Input interval file
   -o, --output_file=o:      Output MAF file
"""

#import psyco_full

import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse

import bx.align.maf
from bx import interval_index_file
import bx.intervals.io
import tempfile
import os, sys

def __main__():

    # Parse Command Line

    options, args = doc_optparse.parse( __doc__ )
    
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
    
    #index maf for use here
    indexes = interval_index_file.Indexes()
    
    try:
        maf_reader = bx.align.maf.Reader( open( mafFile ) )
        # Need to be a bit tricky in our iteration here to get the 'tells' right
        while 1:
            pos = maf_reader.file.tell()
            block = maf_reader.next()
            if block is None: break
            for c in block.components:
                indexes.add( c.src, c.forward_strand_start, c.forward_strand_end, pos )
        index_filename = tempfile.NamedTemporaryFile().name
        out = open(index_filename,'w')
        indexes.write(out)
        out.close()
    except:
        print >>sys.stderr, "Your MAF file appears to be malformed."
        sys.exit()
    
    index = bx.align.maf.Indexed(mafFile, index_filename = index_filename, keep_open=True, parse_e_rows=True)
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
                    out.write( sliced )
                    num_blocks+=1
        except Exception, e:
            print "Error found on input line:",num_lines
            print e
            continue
    #Close output MAF
    out.close()
    #Delete index file
    os.unlink(index_filename)
    print num_blocks, "MAF blocks extracted."
if __name__ == "__main__": __main__()