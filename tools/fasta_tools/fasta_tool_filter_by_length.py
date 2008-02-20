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
        each_line = each_line.rstrip('\n')
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
    min_length = int(sys.argv[2])
    max_length = int(sys.argv[3])
    output_filename = sys.argv[4]
    
    input_handle = open(input_filename, 'r')
    parse_fasta_format(input_handle)
    input_handle.close()
    
    output_handle = open(output_filename, 'w')
    title_keys = seq_hash.keys()
    title_keys.sort()
    at_least_one = 0
    for (i, fasta_title) in title_keys:
        tmp_seq = seq_hash[(i, fasta_title)]
        if (max_length <= 0): 
            compare_max_length = len(tmp_seq)+1
        else:
            compare_max_length = max_length 
        if (len(tmp_seq) >= min_length and len(tmp_seq) <= compare_max_length):
            at_least_one += 1
            print >> output_handle, "%s" %fasta_title
            l = len(tmp_seq)
            c = 0
            s = tmp_seq
            while c < l:
                b = min( c + 50, l )
                print >> output_handle, s[c:b]    
                c = b
    if at_least_one == 0: print >> sys.stdout, "There is no sequence that falls within your range."
            
    output_handle.close()
    return 0

if __name__ == "__main__" : __main__()