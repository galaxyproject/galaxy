#!/usr/bin/env python

import sys

from galaxy.util.checkers import is_gzip


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
        sys.exit("Conversion is only possible for uncompressed files")

    current_line = 0
    sequences = 1000000
    lines_per_chunk = 4 * sequences
    chunk_begin = 0

    with open(input_fname) as in_file, open(sys.argv[2], "w") as out_file:
        out_file.write('{"sections" : [')

        for _ in iter(in_file.readline, ""):
            current_line += 1
            if 0 == current_line % lines_per_chunk:
                chunk_end = in_file.tell()
                out_file.write(f'{{"start":"{chunk_begin}","end":"{chunk_end}","sequences":"{sequences}"}},')
                chunk_begin = chunk_end

        chunk_end = in_file.tell()
        out_file.write(
            f'{{"start":"{chunk_begin}","end":"{chunk_end}","sequences":"{current_line % lines_per_chunk / 4}"}}'
        )
        out_file.write("]}\n")


if __name__ == "__main__":
    main()
