#!/usr/bin/env python

import sys, os, gzip
from galaxy.datatypes.checkers import is_gzip


def main():
    """
    The format of the file is JSON::

        { "sections" : [
                { "start" : "x", "end" : "y", "sequences" : "z" },
                ...
        ]}

    This works only for UNCOMPRESSED fastq files. The Python GzipFile does not provide seekable
    offsets via tell(), so clients just have to split the slow way
    """
    input_fname = sys.argv[1]
    if is_gzip(input_fname):
        print 'Conversion is only possible for uncompressed files'
        sys.exit(1)

    out_file = open(sys.argv[2], 'w')

    current_line = 0
    sequences=1000000
    lines_per_chunk = 4*sequences
    chunk_begin = 0

    in_file = open(input_fname)

    out_file.write('{"sections" : [');

    for line in in_file:
        current_line += 1
        if 0 == current_line % lines_per_chunk:
            chunk_end = in_file.tell()
            out_file.write('{"start":"%s","end":"%s","sequences":"%s"},' % (chunk_begin, chunk_end, sequences))
            chunk_begin = chunk_end

    chunk_end = in_file.tell()
    out_file.write('{"start":"%s","end":"%s","sequences":"%s"}' % (chunk_begin, chunk_end, (current_line % lines_per_chunk) / 4))
    out_file.write(']}\n')


if __name__ == "__main__":
    main()
