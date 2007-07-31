#!/usr/bin/env python

"""
Fix errors in a dataset.
For now, only removing erroneous lines is supported.

usage: %prog input errorsfile output
    -x, --ext: dataset extension (type)
    -m, --methods=N: comma separated list of repair methods
"""

import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse

from galaxy import util

def main():
    options, args = doc_optparse.parse( __doc__ )
    methods = []
    try:
        if options.methods: methods = options.methods.split(",")
    except:
        pass
    
    ext = options.ext

    in_file = open(args[0], "r")
    error_file = open(args[1], "r")
    out_file = open(args[2], "w")

    # string_to_object errors
    error_list = util.string_to_object(error_file.read())
    # index by error type and then by line number
    error_lines = {}
    error_types = {}
    for error in error_list:
        if error.linenum:
            if error.linenum in error_lines:
                error_lines[error.linenum].append(error)
            else:
                error_lines[error.linenum] = [error]
        error_type = error.__class__.__name__
        if error_type in error_types:
            error_types[error_type].append(error)
        else:
            error_types[error_type] = [error]

    linenum = 0
    for line in in_file:
        linenum += 1
        # write unless
        if "lines" in methods:
            if linenum in error_lines:
                line = None
            # other processing here?
        if line:
            out_file.write(line)
    
if __name__ == "__main__":
    main()
