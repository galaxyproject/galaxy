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
    sys.exit(msg)


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

        with open(output, 'w') as out:
            # sed header
            if header_lines > 0:
                sed_header = ['sed', '-n', "1,%dp" % header_lines, input]
                subprocess.check_call(sed_header, stdout=out)

            # grep comments
            grep_comments = ['grep', '^#', input]
            exit_code = subprocess.call(grep_comments, stdout=out)
            if exit_code not in [0, 1]:
                stop_err('Searching for comment lines failed')

            # grep and sort columns
            sed_header_restore = ""
            if header_lines > 0:
                sed_header_restore = "sed '1,%dd' | " % (header_lines)
            sort_columns = "(cat %s | %s grep '^[^#]' | sort -f -t '\t' %s)" % (input, sed_header_restore, ' '.join(key))
            subprocess.check_call(sort_columns, stdout=out, shell=True)

    except Exception as ex:
        stop_err('Error running sorter.py\n' + str(ex))

    # exit
    sys.exit(0)


if __name__ == "__main__":
    main()
