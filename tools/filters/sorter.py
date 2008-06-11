# Filename: sorter.py
# Author: Ian N. Schenck
# Version: 8/22/2005
#
# This script sorts a file based on the inputs: 
# -cols		- column to sort on
# -order	- ASC or DESC-ing order
# -i		- input filename 
# -o		- output filename

import string
import sys
import re
import commands
from os import environ

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
	print " -o	Output filename"
	print " -i	Input filename"
	print " -cols	Column to sort (base 1)"
	print " -order  ASC or DESC"
        print " -style  num or alpha"
	return 0

    outputfile = opts.get("-o")
    if outputfile == None:
	print "No output file specified."
	return -1

    inputfile = opts.get("-i")
    if inputfile == None:
	print "No input file specified."
	return -2

    column = opts.get("-cols")
    if column == None or column == 'None':
	print "Sort column not specified."
	return -3

    order = opts.get("-order")
    if order == None:
	print "Sort order not specified."
	return -4

    style = opts.get("-style")
    if style == None:
        style = "num"

    # At this point, all command line options have been collected.
    # Verify arguments are valid.

    fileRegEx = re.compile("^[A-Za-z0-9./\-_]+$")
    numberRegEx = re.compile("^[0-9]+$")
    sortRegEx = re.compile("^(ASC|DESC)$")
    if not fileRegEx.match(outputfile):
	print "Illegal output filename."
	return -5
    if not fileRegEx.match(inputfile):
	print "Illegal input filename."
	return -6
    if not numberRegEx.match(column):
	print "Column number not an integer."
	return -7
    if not sortRegEx.match(order):
	print "Sort order must be ASCending or DESCending."
	return -8

    # Check sort column against max columns in input file.
    
    column = string.atoi(column)
    if column > len( open(inputfile).readline().split('\t') ):
	print "Column "+str(column)+" does not exist."
	return -9

    # Everything is kosher.

    if order == "DESC":
	order = " -r"
    else:
	order = ""

    if style == "num":
        style = " -n "
    else:
        style = " "
        
    # Launch sort.
    
    environ['LC_ALL'] = 'POSIX'
    commandline = "sort -f"+style+"-k "+str(column)+" -o "+outputfile+" "+inputfile+order

    errorcode, stdout = commands.getstatusoutput(commandline)

    return errorcode

if __name__ == "__main__":
    main()
