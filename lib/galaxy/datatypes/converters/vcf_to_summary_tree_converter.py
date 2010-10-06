#!/usr/bin/env python

"""
Convert from VCF file to summary tree file.

usage: %prog in_file out_file
"""
from __future__ import division

import optparse
import galaxy_utils.sequence.vcf
from galaxy.visualization.tracks.summary import SummaryTree

def main():
    # Read options, args.
    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()
    in_file, out_file = args
        
    # Do conversion.
    st = SummaryTree(block_size=25, levels=6, draw_cutoff=150, detail_cutoff=30)
    for line in list( galaxy_utils.sequence.vcf.Reader( open( in_file ) ) ):
        # VCF format provides a chrom and 1-based position for each variant. 
        # SummaryTree expects 0-based coordinates.
        st.insert_range( line.chrom, long( line.pos-1 ), long( line.pos ) )
    
    st.write(out_file)

if __name__ == "__main__": 
    main()