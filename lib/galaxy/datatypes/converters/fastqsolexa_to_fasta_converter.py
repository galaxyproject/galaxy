#!/usr/bin/env python
"""
convert fastqsolexa file to separated sequence and quality files.

assume each sequence and quality score are contained in one line
the order should be:
1st line: @title_of_seq
2nd line: nucleotides
3rd line: +title_of_qualityscore (might be skipped)
4th line: quality scores
(in three forms: a. digits, b. ASCII codes, the first char as the coding base, c. ASCII codes without the first char.)

Usage:
%python fastqsolexa_to_fasta_converter.py <your_fastqsolexa_filename> <output_seq_filename> <output_score_filename>
"""
import sys

assert sys.version_info[:2] >= (2, 4)


def stop_err(msg):
    sys.stderr.write("%s" % msg)
    sys.exit()


def __main__():
    infile_name = sys.argv[1]
    fastq_block_lines = 0
    seq_title_startswith = ''

    with open(infile_name) as fh, open(sys.argv[2], 'w') as outfile:
        for i, line in enumerate(fh):
            line = line.rstrip()  # eliminate trailing space and new line characters
            if not line or line.startswith('#'):
                continue
            fastq_block_lines = (fastq_block_lines + 1) % 4
            line_startswith = line[0:1]
            if fastq_block_lines == 1:
                # line 1 is sequence title
                if not seq_title_startswith:
                    seq_title_startswith = line_startswith
                if seq_title_startswith != line_startswith:
                    stop_err('Invalid fastqsolexa format at line %d: %s.' % (i + 1, line))
                outfile.write('>%s\n' % line[1:])
            elif fastq_block_lines == 2:
                # line 2 is nucleotides
                outfile.write('%s\n' % line)
            else:
                pass


if __name__ == "__main__":
    __main__()
