#!/usr/bin/env python
"""
Script to mutate SNP codons.
Dan Blankenberg
"""

import sys, string

def strandify( fields, column ):
    strand = '+'
    if column >= 0 and column < len( fields ):
        strand = fields[ column ]
        if strand not in [ '+', '-' ]:
            strand = '+'
    return strand

def main():
    # parse command line
    input_file = sys.argv[1]
    out = open( sys.argv[2], 'wb+' )
    codon_chrom_col = int( sys.argv[3] ) - 1
    codon_start_col = int( sys.argv[4] ) - 1
    codon_end_col = int( sys.argv[5] ) - 1
    codon_strand_col = int( sys.argv[6] ) - 1
    codon_seq_col = int( sys.argv[7] ) - 1
    
    snp_chrom_col = int( sys.argv[8] ) - 1
    snp_start_col = int( sys.argv[9] ) - 1
    snp_end_col = int( sys.argv[10] ) - 1
    snp_strand_col = int( sys.argv[11] ) - 1
    snp_observed_col = int( sys.argv[12] ) - 1
    
    max_field_index = max( codon_chrom_col, codon_start_col, codon_end_col, codon_strand_col, codon_seq_col, snp_chrom_col, snp_start_col, snp_end_col, snp_strand_col, snp_observed_col )
    
    DNA_COMP = string.maketrans( "ACGTacgt", "TGCAtgca" )
    skipped_lines = 0
    for line in open( input_file ):
        line = line.rstrip( '\n\r' )
        if line and not line.startswith( '#' ):
            fields = line.split( '\t' )
            if max_field_index >= len( fields ):
                skipped_lines += 1
                continue
            codon_chrom = fields[codon_chrom_col]
            codon_start = int( fields[codon_start_col] )
            codon_end = int( fields[codon_end_col] )
            codon_strand = strandify( fields, codon_strand_col )
            codon_seq = fields[codon_seq_col].upper()
            
            snp_chrom = fields[snp_chrom_col]
            snp_start = int( fields[snp_start_col] )
            snp_end = int( fields[snp_end_col] )
            snp_strand = strandify( fields, snp_strand_col )
            snp_observed = fields[snp_observed_col].split( '/' )
            
            for observed in snp_observed:
                #Extract DNA on neg strand codons will have positions reversed relative to interval positions; i.e. position 0 == position 2
                offset = snp_start - codon_start
                if codon_strand == '-':
                    offset = 2 - offset
                assert offset >= 0 and offset <= 2, ValueError( 'Impossible offset determined: %s' % offset )
                
                if codon_strand != snp_strand:
                    #if our SNP is on a different strand than our codon, take complement of provided observed SNP base
                    observed = observed.translate( DNA_COMP )
                snp_codon = [ char for char in codon_seq ]
                snp_codon[offset] = observed.upper()
                snp_codon = ''.join( snp_codon )
                
                if codon_seq != snp_codon: #only output when we actually have a different codon
                    out.write( "%s\t%s\n" % ( line, snp_codon )  )

if __name__ == "__main__": main()
