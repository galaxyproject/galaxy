#!/usr/bin/env python
"""
convert SOLiD calor-base data to nucleotide sequence
example: T011213122200221123032111221021210131332222101
         TTGTCATGAGAAAGACAGCCGACACTCAAGTCAACGTATCTCTGGT
"""

import sys, os

def stop_err(msg):
    
    sys.stderr.write(msg)
    sys.stderr.write('\n')
    sys.exit()
    
def color2base(color_seq):

    first_nuc = ['A','C','G','T']
    code_matrix = {}
    code_matrix['0'] = ['A','C','G','T']
    code_matrix['1'] = ['C','A','T','G']
    code_matrix['2'] = ['G','T','A','C']
    code_matrix['3'] = ['T','G','C','A']

    overlap_nuc = ''
    nuc_seq = ''
    
    seq_prefix = prefix = color_seq[0].upper()
    color_seq = color_seq[1:]
                
    if not (seq_prefix in first_nuc):
        stop_err('The leading nucleotide is invalid. Must be one of the four nucleotides: A, T, C, G.\nThe file contains a %s' %seq_prefix )

    for code in color_seq:
        
        if not (code in ['0','1','2','3']):
            stop_err('Expect digits (0, 1, 2, 3) in the color-cading data. File contains numbers other than the set.\nThe file contains a %s' %code)
        
        second_nuc = code_matrix[code]
        overlap_nuc = second_nuc[first_nuc.index(prefix)]
        nuc_seq += overlap_nuc
        prefix = overlap_nuc

    return seq_prefix, nuc_seq

def __main__():

    infilename = sys.argv[1]
    keep_prefix = sys.argv[2].lower()
    outfilename = sys.argv[3]

    outfile = open(outfilename,'w')

    prefix = ''
    color_seq = ''
    for i, line in enumerate(file(infilename)):
        line = line.rstrip('\r\n')

        if not line: continue
        if line.startswith("#"): continue
    
        if line.startswith(">"):
            
            if color_seq:
                prefix, nuc_seq = color2base(color_seq)
                
                if keep_prefix == 'yes':
                    nuc_seq = prefix + nuc_seq
                
                outfile.write(title+'\n')
                outfile.write(nuc_seq+'\n')
                
            title = line
            color_seq = ''
        else:
            color_seq += line
            
    if color_seq:
        prefix, nuc_seq = color2base(color_seq)
                
        if keep_prefix == 'yes':
            nuc_seq = prefix + nuc_seq

        outfile.write(title+'\n')
        outfile.write(nuc_seq+'\n')
            
    outfile.close()
    
if __name__=='__main__': __main__()
