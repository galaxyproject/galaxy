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
    outfile_score = open(sys.argv[2], 'w')    
    
    # guessing the first char used in title lines
    leading_char_quality_title = ''
    leading_char_seq_title = ''
    default_coding_value = 64
    
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
            
        elif every_four_lines == 2: # second line is expected to be read
            read_length = len(line)
            
        elif every_four_lines == 3: # third line is expected to be quality title
            if not leading_char_quality_title:
                leading_char_quality_title = leading_char
            if leading_char != leading_char_quality_title:
                stop_err('Invalid fastq format at line %d.' %(i))    
            quality_title = line[1:]
            
            if (quality_title and (read_title != quality_title)):
                stop_err('Invalid fastq format: titles for sequence and quality score are different.')

            if not quality_title:
                outfile_score.write('>%s\n' %(read_title))
            else:
                outfile_score.write('>%s\n' %(line[1:]))
                
        else:   # fourth line is expected to be the ASCII-coded quality scores 
            qual = ''
            
            # peek: ascii code or digits?
            first_value = line.split()[0]
            
            if first_value.isdigit():
                # digits
                qual = line
            else:
                # ascii code
                # guess leading char
                quality_score_length = len(line)
                if quality_score_length == (read_length+1): # first char is leading_char_score
                    leading_char_score = ord(line[0:1])
                    line = line[1:]
                elif quality_score_length == read_length:
                    leading_char_score = default_coding_value                 # default
                else:
                    stop_err('Invalid fastq format: the number of quality scores is not the same as bases.')
                        
                for j, char in enumerate(line):
                    score = ord(char)-leading_char_score    # 64
                    qual += (str(score) + ' ')
                    
            outfile_score.write('%s\n' %(qual))
                            
    outfile_score.close()
    
    