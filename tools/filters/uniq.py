# Filename: uniq.py
# Author: Ian N. Schenck
# Version: 19/12/2005
#
# This script accepts an input file, an output file, a column
# delimiter, and a list of columns.  The script then grabs unique
# lines based on the columns, and returns those records with a count
# of occurences of each unique column (ignoring trailing spaces),
# inserted before the columns.
#
# This executes the command pipeline:
#       cut -f $fields | sort  | uniq -C
#
# -i            Input file
# -o            Output file
# -d            Delimiter
# -c            Column list (Comma Seperated)
from __future__ import print_function

import re
import subprocess
import sys


# This function is exceedingly useful, perhaps package for reuse?
def getopts(argv):
    opts = {}
    while argv:
        if argv[0][0] == "-":
            opts[argv[0]] = argv[1]
            argv = argv[2:]
        else:
            argv = argv[1:]
    return opts


def main():
    args = sys.argv[1:]

    try:
        opts = getopts(args)
    except IndexError:
        print("Usage:")
        print(" -i        Input file")
        print(" -o        Output file")
        print(" -c        Column list (comma seperated)")
        print(" -d        Delimiter:")
        print("                     T   Tab")
        print("                     C   Comma")
        print("                     D   Dash")
        print("                     U   Underscore")
        print("                     P   Pipe")
        print("                     Dt  Dot")
        print("                     Sp  Space")
        print(" -s        Sorting: value (default), largest, or smallest")
        return 0

    outputfile = opts.get("-o")
    if outputfile is None:
        print("No output file specified.")
        return -1

    inputfile = opts.get("-i")
    if inputfile is None:
        print("No input file specified.")
        return -2

    delim = opts.get("-d")
    if delim is None:
        print("Field delimiter not specified.")
        return -3

    columns = opts.get("-c")
    if columns is None or columns == "None":
        print("Columns not specified.")
        return -4

    sorting = opts.get("-s")
    if sorting is None:
        sorting = "value"
    if sorting not in ["value", "largest", "smallest"]:
        print("Unknown sorting option %r" % sorting)
        return -5

    # All inputs have been specified at this point, now validate.
    fileRegEx = re.compile(r"^[A-Za-z0-9./\-_]+$")
    columnRegEx = re.compile("([0-9]{1,},?)+")

    if not columnRegEx.match(columns):
        print("Illegal column specification.")
        return -4
    if not fileRegEx.match(outputfile):
        print("Illegal output filename.")
        return -5
    if not fileRegEx.match(inputfile):
        print("Illegal input filename.")
        return -6

    column_list = re.split(",", columns)
    columns_for_display = "c" + ", c".join(column_list)

    commandline = "cut "
    # Set delimiter
    if delim == "C":
        commandline += '-d "," '
    if delim == "D":
        commandline += '-d "-" '
    if delim == "U":
        commandline += '-d "_" '
    if delim == "P":
        commandline += '-d "|" '
    if delim == "Dt":
        commandline += '-d "." '
    if delim == "Sp":
        commandline += '-d " " '

    # set columns
    commandline += "-f " + columns
    # we want to remove *trailing* spaces from each field,
    # so look for spaces then tab (for first and middle selected columns)
    # and replace with just tab, and remove any spaces at end of the line
    # (for the final selected column):
    commandline += " " + inputfile + r" | sed 's/\ *\t/\t/' | sed 's/\ *$//'"
    commandline += " | sort | uniq -c"
    # uniq -C puts counts at the start, so we can sort lines by numerical value
    if sorting == "largest":
        commandline += " | sort -n -r"
    elif sorting == "smallest":
        commandline += " | sort -n"
    # uniq -C produces lines with leading spaces, use sed to remove that
    # uniq -C puts a space between the count and the field, want a tab.
    # To replace just first tab, use sed again with 1 as the index
    commandline += r" | sed 's/^\ *//' | sed 's/ /\t/1' > " + outputfile
    errorcode = subprocess.call(commandline, shell=True)

    print("Count of unique values in " + columns_for_display)
    return errorcode


if __name__ == "__main__":
    main()
