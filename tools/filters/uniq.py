# Filename: uniq.py
# Author: Ian N. Schenck
# Version: 19/12/2005
#
# This script accepts an input file, an output file, a column
# delimiter, and a list of columns.  The script then grabs unique
# lines based on the columns, and returns those records with a count
# of occurences of each unique column, inserted before the columns.
#
# This executes the command pipeline:
#       cut -f $fields | sort  | uniq -C
#
# -i            Input file
# -o            Output file
# -d            Delimiter
# -c            Column list (Comma Seperated)

import sys
import re
import string
import commands

# This function is exceedingly useful, perhaps package for reuse?
def getopts(argv):
    opts = {}
    while argv:
        if argv[0][0] == '-':
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
        print "Usage:"
        print " -i        Input file"
        print " -o        Output file"
        print " -c        Column list (comma seperated)"
        print " -d        Delimiter:"
        print "                     T   Tab"
        print "                     C   Comma"
        print "                     D   Dash"
        print "                     U   Underscore"
        print "                     P   Pipe"
        print "                     Dt  Dot"
        print "                     Sp  Space"
        return 0

    outputfile = opts.get("-o")
    if outputfile == None:
        print "No output file specified."
        return -1
    
    inputfile = opts.get("-i")
    if inputfile == None:
        print "No input file specified."
        return -2

    delim = opts.get("-d")
    if delim == None:
        print "Field delimiter not specified."
        return -3

    columns = opts.get("-c")
    if columns == None or columns == 'None':
        print "Columns not specified."
        return -4

    # All inputs have been specified at this point, now validate.
    fileRegEx = re.compile("^[A-Za-z0-9./\-_]+$")
    columnRegEx = re.compile("([0-9]{1,},?)+")

    if not columnRegEx.match(columns):
        print "Illegal column specification."
        return -4
    if not fileRegEx.match(outputfile):
        print "Illegal output filename."
        return -5
    if not fileRegEx.match(inputfile):
        print "Illegal input filename."
        return -6

    column_list = re.split(",",columns)
    columns_for_display = ""
    for col in column_list:
        columns_for_display += "c"+col+", "

    commandline = "cut "
    # Set delimiter
    if delim=='C':
        commandline += "-d \",\" "
    if delim=='D':
        commandline += "-d \"-\" "
    if delim=='U':
        commandline += "-d \"_\" "
    if delim=='P':
        commandline += "-d \"|\" "
    if delim=='Dt':
        commandline += "-d \".\" "
    if delim=='Sp':
        commandline += "-d \" \" "

    # set columns
    commandline += "-f " + columns
    commandline += " " + inputfile + " | sed s/\ //g | sort | uniq -c | sed s/^\ *// | tr \" \" \"\t\" > " + outputfile
    errorcode, stdout = commands.getstatusoutput(commandline)
    
    print "Count of unique values in " + columns_for_display
    return errorcode

if __name__ == "__main__":
    main()
