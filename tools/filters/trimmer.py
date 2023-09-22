#!/usr/bin/env python
from __future__ import print_function

import optparse
import sys


def stop_err(msg):
    sys.exit(msg)


def main():
    usage = """%prog [options]

options (listed below) default to 'None' if omitted
    """
    parser = optparse.OptionParser(usage=usage)

    parser.add_option(
        "-a",
        "--ascii",
        action="store_true",
        default=False,
        help="Use ascii codes to defined ignored beginnings instead of raw characters",
    )

    parser.add_option(
        "-q",
        "--fastq",
        action="store_true",
        default=False,
        help="The input data in fastq format. It selected the script skips every even line since they contain sequence ids",
    )

    parser.add_option(
        "-i",
        "--ignore",
        help='A comma separated list on ignored beginnings (e.g., ">,@"), or its ascii codes (e.g., "60,42") if option -a is enabled',
    )

    parser.add_option("-s", "--start", type="int", default=0, help="Trim from beginning to here (1-based)")

    parser.add_option("-e", "--end", type="int", default="0", help="Trim from here to the ned (1-based)")

    parser.add_option(
        "-f", "--file", dest="input_txt", default=False, help="Name of file to be chopped. STDIN is default"
    )

    parser.add_option(
        "-c", "--column", type="int", dest="col", default="0", help="Column to chop. If 0 = chop the whole line"
    )

    options, args = parser.parse_args()
    invalid_starts = []

    if options.input_txt:
        infile = open(options.input_txt)
    else:
        infile = sys.stdin

    if options.ignore and options.ignore != "None":
        invalid_starts = {chr(int(c)) if options.ascii else c for c in options.ignore.split(",")}

    for i, line in enumerate(infile):
        line = line.rstrip("\r\n")
        if line:
            if options.fastq and i % 2 == 0:
                print(line)
                continue

            if line[0] not in invalid_starts:
                if options.col == 0:
                    if options.end == 0:
                        line = line[options.start - 1 :]
                    else:
                        line = line[options.start - 1 : options.end]
                else:
                    fields = line.split("\t")
                    if options.col > len(fields):
                        stop_err("Column %d does not exist. Check input parameters\n" % options.col)

                    if options.end == 0:
                        fields[options.col - 1] = fields[options.col - 1][options.start - 1 :]
                    else:
                        fields[options.col - 1] = fields[options.col - 1][options.start - 1 : options.end]
                    line = "\t".join(fields)
            print(line)


if __name__ == "__main__":
    main()
