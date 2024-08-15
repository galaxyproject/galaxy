# Filename: grep.py
# Author: Ian N. Schenck
# Version: 8/23/2005
#
# This script accepts regular expressions, as well as an "invert"
# option, and applies the regular expression using grep.  This wrapper
# provides security and pipeline.
#
# Grep is launched based on these inputs:
# -i Input file
# -o Output file
# -pattern RegEx pattern
# -v true or false (output NON-matching lines)
from __future__ import print_function

import os
import re
import subprocess
import sys
from subprocess import (
    PIPE,
    Popen,
)
from tempfile import NamedTemporaryFile


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
        print(" -i Input file")
        print(" -o Output file")
        print(" -pattern RegEx pattern")
        print(" -v true or false (Invert match)")
        return 0

    outputfile = opts.get("-o")
    if outputfile is None:
        print("No output file specified.")
        return -1

    inputfile = opts.get("-i")
    if inputfile is None:
        print("No input file specified.")
        return -2

    invert = opts.get("-v")
    if invert is None:
        print("Match style (Invert or normal) not specified.")
        return -3

    pattern = opts.get("-pattern")
    if pattern is None:
        print("RegEx pattern not specified.")
        return -4

    # All inputs have been specified at this point, now validate.

    # replace if input has been escaped, remove sq
    # characters that are allowed but need to be escaped
    mapped_chars = {
        ">": "__gt__",
        "<": "__lt__",
        "'": "__sq__",
        '"': "__dq__",
        "[": "__ob__",
        "]": "__cb__",
        "{": "__oc__",
        "}": "__cc__",
    }

    # with new sanitizing we only need to replace for single quote,
    # but this needs to remain for backwards compatibility
    for key, value in mapped_chars.items():
        pattern = pattern.replace(value, key)

    # match filename and invert flag
    fileRegEx = re.compile(r"^[A-Za-z0-9./\-_]+$")
    invertRegEx = re.compile(r"(true)|(false)")

    # verify that filename and inversion flag are in the correct format
    if not fileRegEx.match(outputfile):
        print("Illegal output filename.")
        return -5
    if not fileRegEx.match(inputfile):
        print("Illegal input filename.")
        return -6
    if not invertRegEx.match(invert):
        print("Illegal invert option.")
        return -7

    # invert grep search?
    if invert == "true":
        invertflag = "-v"
        print("Not matching pattern: %s" % pattern)
    else:
        invertflag = ""
        print("Matching pattern: %s" % pattern)

    # set version flag
    versionflag = "-P"

    # MacOS 10.8.2 does not support -P option for perl-regex anymore
    versionmatch = Popen("grep -V | grep 'BSD'", shell=True, stdout=PIPE).communicate()[0]
    if versionmatch:
        versionflag = "-E"

    # create temp file holding pattern
    # by using a file to hold the pattern, we don't have worry about sanitizing grep commandline and can include single quotes in pattern
    pattern_file_name = NamedTemporaryFile().name
    open(pattern_file_name, "w").write(pattern)

    # generate grep command
    commandline = "grep %s %s -f %s %s > %s" % (versionflag, invertflag, pattern_file_name, inputfile, outputfile)

    # run grep
    errorcode = subprocess.call(commandline, shell=True)

    # remove temp pattern file
    os.unlink(pattern_file_name)

    # return error code
    return errorcode


if __name__ == "__main__":
    main()
