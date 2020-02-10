#!/usr/bin/env python
"""
Uses the python csv library to convert to and from tabular

usage: %prog [--from-tabular] -i in_file -o out_file
"""

import argparse
import csv
import sys

from contextlib import contextmanager

@contextmanager
def compat_open(file, mode):
    if sys.version_info[0] > 2:
        fh = open(file, mode, newline='')
    else:
        fh = open(file, mode + 'b')
    try:
        yield fh
    finally:
        fh.close()

def main():
    usage = "Usage: %prog [options]"
    parser = argparse.ArgumentParser(usage=usage)
    parser.add_argument('-f', '--from-tabular', action='store_true', default=False, dest='fromtabular')
    parser.add_argument('-i', '--input', type=str, dest='input')
    parser.add_argument('-o', '--output', type=str, dest='output')
    args = parser.parse_args()
    input_fname = args.input
    output_fname = args.output
    if args.fromtabular:
        convert_to_csv(input_fname, output_fname)
    else:
        convert_to_tsv(input_fname, output_fname)


def convert_to_tsv(input_fname, output_fname):
    with compat_open(input_fname, 'r') as csvfile:
        with compat_open(output_fname, 'w') as ofh:
            reader = csv.reader(csvfile)
            for line in reader:
                ofh.write('\t'.join(line) + '\n')


def convert_to_csv(input_fname, output_fname):
    with compat_open(input_fname, 'r') as tabfile:
        with compat_open(output_fname, 'w') as ofh:
            writer = csv.writer(ofh, delimiter=',')
            for line in tabfile.readlines():
                writer.writerow(line.strip().split('\t'))


if __name__ == "__main__":
    main()
