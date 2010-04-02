#!/usr/bin/env python

"""
Split fixed length paired end reads
"""

import os, sys

if __name__ == '__main__':
    
    infile = sys.argv[1]
    outfile_end1 = open(sys.argv[2], 'w')
    outfile_end2 = open(sys.argv[3], 'w')
    
    i = 0
    
    for line in file( infile ):
        line = line.rstrip()
        
        if not line:
            continue 
        
        end1 = ''
        end2 = ''
        
        line_index = i % 4
        
        if line_index == 0:
            end1 = line + '/1'
            end2 = line + '/2'
        
        elif line_index == 1:
            seq_len = len(line)/2
            end1 = line[0:seq_len]
            end2 = line[seq_len:]
        
        elif line_index == 2:
            end1 = line + '/1'
            end2 = line + '/2'
        
        else:
            qual_len = len(line)/2
            end1 = line[0:qual_len]
            end2 = line[qual_len:]
            
        outfile_end1.write('%s\n' %(end1))
        outfile_end2.write('%s\n' %(end2))
        
        i += 1
        
    if  i % 4 != 0  :
        sys.stderr.write("WARNING: Number of lines in the input file was not divisible by 4.\nCheck consistency of the input fastq file.\n")
    outfile_end1.close()
    outfile_end2.close()    