# Filename: grep.py
# Author: Ian N. Schenck
# Version: 8/23/2005
#
# This script accepts regular expressions, as well as an "invert"
# option, and applies the regular expression using grep.  This wrapper
# provides security and pipeline.
#
# Grep is launched based on these inputs:
# -i		Input file
# -o		Output file
# -pattern	RegEx pattern
# -v	        true or false (output NON-matching lines)

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
	print " -i		Input file"
	print " -o		Output file"
	print " -pattern	RegEx pattern"
	print " -v		true or false (Invert match)"
	return 0

    outputfile = opts.get("-o")
    if outputfile == None:
	print "No output file specified."
	return -1
    
    inputfile = opts.get("-i")
    if inputfile == None:
	print "No input file specified."
	return -2

    invert = opts.get("-v")
    if invert == None:
	print "Match style (Invert or normal) not specified."
	return -3

    pattern = opts.get("-pattern")
    if pattern == None:
	print "RegEx pattern not specified."
	return -4

    # All inputs have been specified at this point, now validate.

    # replace if input has been escaped, remove sq
    # characters that are allowed but need to be escaped
    mapped_chars = { '>' :'__gt__', 
                 '<' :'__lt__', 
                 '\'' :'__sq__',
                 '"' :'__dq__',
                 '[' :'__ob__',
                 ']' :'__cb__',
		 '{' :'__oc__',
                 '}' :'__cc__',

                 }

    for key, value in mapped_chars.items():
        pattern = pattern.replace(value, key)

    pattern = pattern.replace('\'', '')

    fileRegEx = re.compile("^[A-Za-z0-9./\-_]+$")
    invertRegEx = re.compile("(true)|(false)")

    if not fileRegEx.match(outputfile):
	print "Illegal output filename."
	return -5
    if not fileRegEx.match(inputfile):
	print "Illegal input filename."
	return -6
    if not invertRegEx.match(invert):
	print "Illegal invert option."
	return -7

    # grep
    if invert == "true":
	invertflag = " -v"
    else:
	invertflag = ""

    commandline = "grep -E"+invertflag+" '"+pattern+"' "+inputfile+" > "+outputfile

    errorcode, stdout = commands.getstatusoutput(commandline)
    
    return errorcode

if __name__ == "__main__":
    main()
