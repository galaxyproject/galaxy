#!/usr/bin/env python2.4
#Dan Blankenberg
"""
Reads a list of intervals and a maf. Outputs a new set of intervals with statistics appended.
"""

import sys, tempfile
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align
import bx.align.maf
import bx.intervals.io
import bx.interval_index_file
import psyco_full

def __main__():

    input_maf_filename = sys.argv[1].strip()
    input_interval_filename = sys.argv[2].strip()
    output_filename = sys.argv[3].strip()
    dbkey = sys.argv[4].strip()
    chr_col  = int(sys.argv[5].strip())-1
    start_col = int(sys.argv[6].strip())-1
    end_col = int(sys.argv[7].strip())-1
    
    #index maf for use here
    indexes = bx.interval_index_file.Indexes()
    maf_reader = bx.align.maf.Reader( open( input_maf_filename ) )
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
    index = bx.align.maf.Indexed(input_maf_filename, index_filename = index_filename)
    
    out = open(output_filename, 'w')
    
    num_region = 0
    #loop through interval file
    for region in bx.intervals.io.GenomicIntervalReader( open(input_interval_filename, 'r' ), chrom_col=chr_col, start_col=start_col, end_col=end_col, fix_strand=True):
        sequences = {dbkey: [ False for i in range( region.end - region.start)]}
        
        src = dbkey + "." + region.chrom
        start = region.start
        end = region.end
        
        blocks = index.get( src, start, end )
        for maf in blocks:
            #make sure all species are known
            for c in maf.components:
                spec = bx.align.src_split(c.src)[0]
                if spec not in sequences: sequences[spec] = [ False for i in range( region.end - region.start)]
            
            #save old score here for later use, since slice results score==0
            old_score =  maf.score
            
            #slice maf by start and end
            ref = maf.get_component_by_src( bx.align.src_merge(dbkey, region.chrom) )
            slice_start = max( start, ref.start )
            slice_end = min( end, ref.end )
            sliced = maf.slice_by_component( ref, slice_start, slice_end ) 
            
            #look for gaps (indels) in primary sequence, we do not include these columns in our stats
            gaps = []
            for i in range(len(ref.text)):
                if ref.text[i] in ['-']:
                    gaps.append(i)
            
            #Set nucleotide containing columns
            for c in sliced.components:
                spec = bx.align.src_split(c.src)[0]
                gap_offset = 0
                for i in range(len(c.text)):
                    if i in gaps: gap_offset += 1
                    elif c.text[i] not in ['-']: sequences[spec][i-gap_offset+slice_start-start] = True
            
        #print sequences
        out.write("%s\t%s\t%s\t%s\n" % ( "\t".join(region.fields), dbkey, sequences[dbkey].count(True), sequences[dbkey].count(False) ) )
        keys = sequences.keys()
        keys.remove(dbkey)
        keys.sort()
        for key in keys:
            out.write("%s\t%s\t%s\t%s\n" % ( "\t".join(region.fields), key, sequences[key].count(True), sequences[key].count(False) ) )
        num_region += 1
    print "%i regions were processed." % num_region
    out.close()
if __name__ == "__main__": __main__()
