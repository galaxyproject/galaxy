#! /usr/bin/python

"""
Split Solexa paired end reads
"""

import os, sys

if __name__ == '__main__':
    
    infile = sys.argv[1]
    outfile_end1 = open(sys.argv[2], 'w')
    outfile_end2 = open(sys.argv[3], 'w')
    
    for i, line in enumerate(file(infile)):
        line = line.rstrip()
        if not line or line.startswith('#'): continue
        
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
        
    outfile_end1.close()
    outfile_end2.close()    