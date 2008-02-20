#! /usr/bin/python
"""
Input: fasta, minimal length, maximal length
Output: fasta
Return sequences whose lengths are within the range.
"""

import sys, os

seq_hash = {}

def parse_fasta_format(file_handle):    

    tmp_title = ''
    tmp_seq = ''
    tmp_seq_count = 0
    for i, each_line in enumerate(file_handle):
        each_line = each_line.rstrip('\r\n')
        if (each_line[0] == '>'):
            if (len(tmp_seq) > 0):
                tmp_seq_count += 1
                seq_hash[(tmp_seq_count, tmp_title)] = tmp_seq
            tmp_title = each_line
            tmp_seq = ''
        else:
            tmp_seq = tmp_seq + each_line
            if (each_line.split()[0].isdigit()):
                tmp_seq = tmp_seq + ' '
    if (len(tmp_seq) > 0):
        seq_hash[(tmp_seq_count, tmp_title)] = tmp_seq
        
    return 0

def __main__():
    
    input_filename = sys.argv[1]
    output_filename = sys.argv[2]
    
    input_handle = open(input_filename, 'r')
    parse_fasta_format(input_handle)
    input_handle.close()
    
    output_handle = open(output_filename, 'w')
    title_keys = seq_hash.keys()
    title_keys.sort()
    for (i, fasta_title) in title_keys:
        tmp_seq = seq_hash[(i, fasta_title)]
        print >> output_handle, "%s\t%d" %(fasta_title, len(tmp_seq))
    output_handle.close()
    return 0

if __name__ == "__main__" : __main__()