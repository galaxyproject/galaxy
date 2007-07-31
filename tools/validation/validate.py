#!/usr/bin/env python

"""
Validate a dataset based on extension a metadata passed in on the
command line.  Outputs a binhex'd representation of the exceptions.

usage: %prog input output
    -m, --metadata=N: base64 pickeled metadata
    -x, --ext=N: extension as understood by galaxy
"""

import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse

from galaxy import model
from fileinput import FileInput
from galaxy import util

def main():
    options, args = doc_optparse.parse( __doc__ )

    try:
        extension = options.ext
    except:
        doc_optparse.exception()

    # create datatype
    data = model.Dataset( extension=extension, id=int( args[0] ) )
    data.file_path = "/home/ian/trunk/database/files/"
    
    if options.metadata:
        data.metadata = util.string_to_object( options.metadata )

    errors = data.datatype.validate( data )
    print util.object_to_string(errors)

if __name__ == "__main__":
    main()
