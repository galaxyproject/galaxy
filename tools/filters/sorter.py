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

import subprocess
import sys
from optparse import OptionParser


def stop_err(msg):
    sys.stderr.write("%s\n" % msg)
    sys.exit()


def main():
    # define options
    parser = OptionParser()
    parser.add_option("-i", "--input")
    parser.add_option("-o", "--output")
    parser.add_option("-k", "--key", action="append")
    parser.add_option("-H", "--header_lines", type='int')

    # parse
    options, args = parser.parse_args()

    try:
        # retrieve options
        input = options.input
        output = options.output
        header_lines = options.header_lines
        key = [" -k" + k for k in options.key]

        # sed header
        if header_lines > 0:
            sed_header = "sed -n '1,%dp' %s > %s" % (header_lines, input, output)
            subprocess.call(sed_header, shell=True)

        # grep comments
        grep_comments = "(grep '^#' %s) >> %s" % (input, output)
        subprocess.call(grep_comments, shell=True)

        # grep and sort columns
        sed_header_restore = ""
        if header_lines > 0:
            sed_header_restore = "sed '1,%dd' | " % (header_lines)
        sort_columns = "(cat %s | %s grep '^[^#]' | sort -f -t '\t' %s) >> %s" % (input, sed_header_restore, ' '.join(key), output)
        subprocess.call(sort_columns, shell=True)

    except Exception as ex:
        stop_err('Error running sorter.py\n' + str(ex))

    # exit
    sys.exit(0)


if __name__ == "__main__":
    main()
