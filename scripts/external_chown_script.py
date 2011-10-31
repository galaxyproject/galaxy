#!/usr/bin/env python
import os
import sys
import errno
import pwd
#import drmaa
new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs
import pkg_resources
pkg_resources.require("simplejson")
import simplejson as json
pkg_resources.require("drmaa")
import drmaa

def validate_paramters():
    if len(sys.argv)<4:
        sys.stderr.write("usage: %s path user_name gid\n" % sys.argv[0])
        exit(1)

    path  = sys.argv[1]
    galaxy_user_name  = sys.argv[2]
    gid  = sys.argv[3]

    return path, galaxy_user_name, gid 

def main():
    path, galaxy_user_name, gid  = validate_paramters()
    os.system('chown -Rh %s %s' %(galaxy_user_name, path))
    os.system('chgrp -Rh %s %s' %(gid, path))

if __name__ == "__main__":
    main()


