#! /usr/bin/python

"""
convert fastq file to separated sequence and quality files.

assume each sequence and quality score are contained in one line
the order should be:
1st line: @title_of_seq
2nd line: nucleotides
3rd line: +title_of_qualityscore (might be skipped)
4th line: quality scores 
(in three forms: a. digits, b. ASCII codes, the first char as the coding base, c. ASCII codes without the first char.)

Usage:
%python convert_fastq2fasta.py <your_fastq_filename> <output_seq_filename> <output_score_filename>
"""

import sys, os
from math import *

assert sys.version_info[:2] >= ( 2, 4 )


def stop_err( msg ):
    
    sys.stderr.write( "%s\n" % msg )
    sys.exit()


if __name__ == '__main__':

    # file I/O
    infile = sys.argv[1]
    outfile_seq = open(sys.argv[2], 'w')
    
    
    # guessing the first char used in title lines
    leading_char_seq_title = ''
    
    every_four_lines = 0
    
    for i, line in enumerate(file(infile)):
        
        line = line.rstrip()    # get rid of the newline and spaces
        
        if ((not line) or (line.startswith('#'))): continue               # comments
        
        every_four_lines = (every_four_lines + 1) % 4
        leading_char = line[0:1]
        
        if every_four_lines == 1:   # first line is expected to be read title
            if not leading_char_seq_title:
                leading_char_seq_title = leading_char
            if leading_char != leading_char_seq_title:
                stop_err('Invalid fastq format at line %d.' %(i))
            read_title = line[1:]
            outfile_seq.write('>%s\n' %(line[1:]))
            
        elif every_four_lines == 2: # second line is expected to be read
            read_length = len(line)
            outfile_seq.write('%s\n' %(line))
        
        else:
            pass

    outfile_seq.close()

    
    