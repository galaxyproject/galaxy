"""
    Sorts tabular data on one or more columns. All comments of the file are collected
    and placed at the beginning of the sorted output file.

    usage: sorter.py [options]
    -i, --input: Tabular file to be sorted
    -o, --output: Sorted output file
    -k, --key: Key (see manual for bash/sort)

    usage: sorter.py input output [key ...]
"""
# 03/05/2013 guerler

import os
import sys
from optparse import OptionParser


def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()


def main():
    # define options
    parser = OptionParser()
    parser.add_option("-i", "--input")
    parser.add_option("-o", "--output")
    parser.add_option("-k", "--key", action="append")

    # parse
    options, args = parser.parse_args()

    try:
        # retrieve options
        input = options.input
        output = options.output
        key = [" -k" + k for k in options.key]

        # grep comments
        grep_comments = "(grep '^#' %s) > %s" % (input, output)

        # grep and sort columns
        sort_columns = "(grep '^[^#]' %s | sort -f -t '\t' %s) >> %s" % (input, ' '.join(key), output)

        # execute
        os.system(grep_comments)
        os.system(sort_columns)

    except Exception as ex:
        stop_err('Error running sorter.py\n' + str(ex))

    # exit
    sys.exit(0)


if __name__ == "__main__":
    main()
