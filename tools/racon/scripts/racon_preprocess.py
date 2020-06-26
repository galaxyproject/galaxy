#!/usr/bin/env python

from __future__ import print_function
import os, sys, argparse

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

#*******************************************************************************

def parse_file(file_name, read_set):
    line_id = 0
    name = ''
    data = ''
    qual = ''
    valid = False
    with (open(file_name)) as f:
        for line in f:
            if (line_id == 0):
                if (valid):
                    if (len(name) == 0 or len(data) == 0 or len(data) != len(qual)):
                        eprint('File is not in FASTQ format')
                        sys.exit(1)
                    valid = False
                    if (name in read_set):
                        print(name + '2')
                    else:
                        read_set.add(name)
                        print(name + '1')
                    print(data)
                    print('+')
                    print(qual)
                name = line.rstrip().split(' ')[0]
                data = ''
                qual = ''
                line_id = 1
            elif (line_id == 1):
                if (line[0] == '+'):
                    line_id = 2
                else:
                    data += line.rstrip()
            elif (line_id == 2):
                qual += line.rstrip()
                if (len(qual) >= len(data)):
                    valid = True
                    line_id = 0

    if (valid):
        if (len(name) == 0 or len(data) == 0 or len(data) != len(qual)):
            eprint(len(name), len(data), len(qual))
            eprint('File is not in FASTQ format')
            sys.exit(1)
        if (name in read_set):
           print(name + '2')
        else:
           read_set.add(name)
           print(name + '1')
        print(data)
        print('+')
        print(qual)

#*******************************************************************************

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='''Script for preprocessing
        Illumina paired-end reads for usage in Racon. Each read will get unique
        header up to the first white space to distinguish those forming a pair.''')
    parser.add_argument('first', help='''File containing the first read of a pair
        or both.''')
    parser.add_argument('second', nargs='?', help='''Optional file containing
        read pairs of the same paired-end sequencing run.''')

    args = parser.parse_args()

    read_set = set()
    parse_file(args.first, read_set)
    if (args.second is not None):
        parse_file(args.second, read_set)
