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
%python fastqsolexa_to_qual_converter.py <your_fastqsolexa_filename> <output_seq_filename> <output_score_filename>
"""
import sys

assert sys.version_info[:2] >= (2, 4)


def stop_err(msg):
    sys.stderr.write("%s" % msg)
    sys.exit()


def __main__():
    infile_name = sys.argv[1]
    # datatype = sys.argv[3]
    qual_title_startswith = ''
    seq_title_startswith = ''
    default_coding_value = 64
    fastq_block_lines = 0

    with open(infile_name) as fh, open(sys.argv[2], 'w') as outfile_score:
        for i, line in enumerate(fh):
            line = line.rstrip()
            if not line or line.startswith('#'):
                continue
            fastq_block_lines = (fastq_block_lines + 1) % 4
            line_startswith = line[0:1]
            if fastq_block_lines == 1:
                # first line is @title_of_seq
                if not seq_title_startswith:
                    seq_title_startswith = line_startswith
                if line_startswith != seq_title_startswith:
                    stop_err('Invalid fastqsolexa format at line %d: %s.' % (i + 1, line))
                read_title = line[1:]
            elif fastq_block_lines == 2:
                # second line is nucleotides
                read_length = len(line)
            elif fastq_block_lines == 3:
                # third line is +title_of_qualityscore (might be skipped)
                if not qual_title_startswith:
                    qual_title_startswith = line_startswith
                if line_startswith != qual_title_startswith:
                    stop_err('Invalid fastqsolexa format at line %d: %s.' % (i + 1, line))
                quality_title = line[1:]
                if quality_title and read_title != quality_title:
                    stop_err('Invalid fastqsolexa format at line %d: sequence title "%s" differes from score title "%s".' % (i + 1, read_title, quality_title))
                if not quality_title:
                    outfile_score.write('>%s\n' % read_title)
                else:
                    outfile_score.write('>%s\n' % line[1:])
            else:
                # fourth line is quality scores
                qual = ''
                fastq_integer = True
                # peek: ascii or digits?
                val = line.split()[0]

                fastq_integer = True
                try:
                    int(val)
                except ValueError:
                    fastq_integer = False

                if fastq_integer:  # digits
                    qual = line
                else:
                    # ascii
                    quality_score_length = len(line)
                    if quality_score_length == read_length + 1:
                        quality_score_startswith = ord(line[0:1])
                        line = line[1:]
                    elif quality_score_length == read_length:
                        quality_score_startswith = default_coding_value
                    else:
                        stop_err('Invalid fastqsolexa format at line %d: the number of quality scores ( %d ) is not the same as bases ( %d ).' % (i + 1, quality_score_length, read_length))
                    for j, char in enumerate(line):
                        score = ord(char) - quality_score_startswith    # 64
                        qual = "%s%s " % (qual, str(score))
                outfile_score.write('%s\n' % qual)


if __name__ == "__main__":
    __main__()
