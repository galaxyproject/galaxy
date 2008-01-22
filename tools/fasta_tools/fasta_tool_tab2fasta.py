#! /usr/bin/python
"""
Input: fasta, minimal length, maximal length
Output: fasta
Return sequences whose lengths are within the range.
Wen-Yu Chung
"""

import sys, os

seq_hash = {}

def __main__():
    
    input_filename = sys.argv[1]
    if (sys.argv[2] != ""): input_titleCol = sys.argv[2]
    else: print >> sys.stderr, "Please indicate columns for the titles and sequences."
    input_seqCol = int(sys.argv[3]) - 1
    output_filename = sys.argv[4]        
    
    if (input_seqCol < 0): print >> sys.stderr, "Column index starts from 1."
      
    titleCols = input_titleCol.split(',')

    # print input_titleCol
    # print input_seqCol
    
    input_handle = open(input_filename, 'r')
    output_handle = open(output_filename, 'w')
    
    # need to check which column is the title, which is the sequence
    for i, line in enumerate(input_handle):
        line = line.strip('\r\n')
        fields = line.split()
        total_columns = len(fields)
        
        if (input_seqCol > total_columns): print >> sys.stderr, "Sequence column does not exist." 
        
        fasta_title = []
        for j in titleCols:
            if (j.isdigit()):
                correct_index = int(j) - 1
                if (correct_index < total_columns) and (correct_index >= 0):
                    fasta_title.append(fields[correct_index])
                else:
                    print >> sys.stderr, "Title column does not exist. Column index starts from 1, not 0."
            else:
                print >> sys.stderr, "Title column is not an index."
                
        fasta_seq = fields[input_seqCol]
        if (fasta_title[0].startswith(">")): fasta_title[0]=fasta_title[0][1:]
        print >> output_handle, ">%s\n%s" %("_".join(fasta_title), fasta_seq)
    
    output_handle.close()    
    input_handle.close()

    return 0

if __name__ == "__main__" : __main__()