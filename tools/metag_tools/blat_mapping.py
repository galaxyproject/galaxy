#!/usr/bin/env python

import os, sys

assert sys.version_info[:2] >= ( 2, 4 )

def reverse_complement(s):
    complement_dna = {"A":"T", "T":"A", "C":"G", "G":"C", "a":"t", "t":"a", "c":"g", "g":"c", "N":"N", "n":"n" , ".":"."}
    reversed_s = []
    for i in s:
        reversed_s.append(complement_dna[i])
    reversed_s.reverse()
    return "".join(reversed_s)
    
def __main__():
    nuc_index = {'a':0,'t':1,'c':2,'g':3,'n':4}
    coverage = {}        # key = (chrom, index)
    invalid_lines = 0
    invalid_chrom = 0
    infile = sys.argv[1]
    outfile = sys.argv[2]

    for i, line in enumerate( open( infile ) ):
        line = line.rstrip('\r\n')
        if not line or line.startswith('#'):
            continue
        fields = line.split()
        if len(fields) < 21:                # standard number of pslx columns
            invalid_lines += 1
            continue 
        if not fields[0].isdigit():
            invalid_lines += 1
            continue
        chrom = fields[13]
        if not chrom.startswith( 'chr' ):
            invalid_lines += 1
            invalid_chrom += 1
            continue
        try:
            block_count = int(fields[17])
        except:
            invalid_lines += 1
            continue
        block_size = fields[18].split(',')
        chrom_start = fields[20].split(',')

        for j in range( block_count ):
            try:
                this_block_size = int(block_size[j])
                this_chrom_start = int(chrom_start[j])
            except:
                invalid_lines += 1
                break
            # brut force coverage                
            for k in range( this_block_size ):
                cur_index = this_chrom_start + k
                if coverage.has_key( ( chrom, cur_index ) ):
                    coverage[(chrom, cur_index)] += 1
                else:
                    coverage[(chrom, cur_index)] = 1
                
    # generate a index file
    outputfh = open(outfile, 'w')
    keys = coverage.keys()
    keys.sort()
    previous_chrom = ''
    for i in keys:
        (chrom, location) = i
        sum = coverage[(i)]
        if chrom != previous_chrom:
            outputfh.write( 'variableStep chrom=%s\n' % ( chrom ) )
            previous_chrom = chrom
        outputfh.write( "%s\t%s\n" % ( location, sum ) )
    outputfh.close()
    
    if invalid_lines:
        invalid_msg = "Skipped %d invalid lines" % invalid_lines
        if invalid_chrom:
            invalid_msg += ", including %d lines with chrom id errors which must begin with 'chr' to map correctly to the UCSC Genome Browser. "
        
if __name__ == '__main__': __main__()