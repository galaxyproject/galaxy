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
    errors = {}
    for name, message in [ ('max_field_index','not enough fields'), ( 'codon_len', 'codon length must be 3' ), ( 'codon_seq', 'codon sequence must have length 3' ), ( 'snp_len', 'SNP length must be 3' ), ( 'snp_observed', 'SNP observed values must have length 3' ), ( 'empty_comment', 'empty or comment'), ( 'no_overlap', 'codon and SNP do not overlap' ) ]:
        errors[ name ] = { 'count':0, 'message':message }
    line_count = 0
    for line_count, line in enumerate( open( input_file ) ):
        line = line.rstrip( '\n\r' )
        if line and not line.startswith( '#' ):
            fields = line.split( '\t' )
            if max_field_index >= len( fields ):
                skipped_lines += 1
                errors[ 'max_field_index' ]['count'] += 1
                continue
            
            #read codon info
            codon_chrom = fields[codon_chrom_col]
            codon_start = int( fields[codon_start_col] )
            codon_end = int( fields[codon_end_col] )
            if codon_end - codon_start != 3:
                #codons must be length 3
                skipped_lines += 1
                errors[ 'codon_len' ]['count'] += 1
                continue
            codon_strand = strandify( fields, codon_strand_col )
            codon_seq = fields[codon_seq_col].upper()
            if len( codon_seq ) != 3:
                #codon sequence must have length 3
                skipped_lines += 1
                errors[ 'codon_seq' ]['count'] += 1
                continue
            
            #read snp info
            snp_chrom = fields[snp_chrom_col]
            snp_start = int( fields[snp_start_col] )
            snp_end = int( fields[snp_end_col] )
            if snp_end - snp_start != 1:
                #snps must be length 1
                skipped_lines += 1
                errors[ 'snp_len' ]['count'] += 1
                continue
            snp_strand = strandify( fields, snp_strand_col )
            snp_observed = fields[snp_observed_col].split( '/' )
            snp_observed = [ observed for observed in snp_observed if len( observed ) == 1 ]
            if not snp_observed:
                #sequence replacements must be length 1
                skipped_lines += 1
                errors[ 'snp_observed' ]['count'] += 1
                continue
            
            #Determine index of replacement for observed values into codon
            offset = snp_start - codon_start
            #Extract DNA on neg strand codons will have positions reversed relative to interval positions; i.e. position 0 == position 2
            if codon_strand == '-':
                offset = 2 - offset
            if offset < 0 or offset > 2: #assert offset >= 0 and offset <= 2, ValueError( 'Impossible offset determined: %s' % offset )
                #codon and snp do not overlap
                skipped_lines += 1
                errors[ 'no_overlap' ]['count'] += 1
                continue
            
            for observed in snp_observed:
                if codon_strand != snp_strand:
                    #if our SNP is on a different strand than our codon, take complement of provided observed SNP base
                    observed = observed.translate( DNA_COMP )
                snp_codon = [ char for char in codon_seq ]
                snp_codon[offset] = observed.upper()
                snp_codon = ''.join( snp_codon )
                
                if codon_seq != snp_codon: #only output when we actually have a different codon
                    out.write( "%s\t%s\n" % ( line, snp_codon )  )
        else:
            skipped_lines += 1
            errors[ 'empty_comment' ]['count'] += 1
    if skipped_lines:
        print "Skipped %i (%4.2f%%) of %i lines; reasons: %s" % ( skipped_lines, ( float( skipped_lines )/float( line_count ) ) * 100, line_count, ', '.join( [ "%s (%i)" % ( error['message'], error['count'] ) for error in errors.itervalues() if error['count'] ] ) )
    
if __name__ == "__main__": main()
