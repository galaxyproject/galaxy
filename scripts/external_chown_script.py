#!/usr/bin/env python
import os
import os.path
import sys

# you may configure the paths below which modifications are allowed.
# should contain the full paths to job_working_directory and new_file_path.
# if set to None every file can be modified by the script.
# this can increase security in particular if write access to this
# script is removed by the admin.
# ALLOWED_PATHS = [ job_working_directory, new_file_path ]
# ALLOWED_PATHS = None 
ALLOWED_PATHS = [ "/gpfs1/data/galaxy_server/galaxy-dev/database/tmp/", "/gpfs1/data/galaxy_server/galaxy-dev/jobs_dir/" ]

def validate_paramters():
    if len(sys.argv) < 4:
        sys.stderr.write("usage: %s path user_name gid\n" % sys.argv[0])
        exit(1)

    path = os.path.abspath( sys.argv[1] )
    if ALLOWED_PATHS == None: 
        allowed = True
    else:
        allowed = False
        for p in ALLOWED_PATHS:
            if path.startswith( p ):
                allowed = True
                break
    if not allowed:
        sys.stderr.write( "owner and group modifications in %s are not allowed\n" %path )
        sys.exit( 1 )

    galaxy_user_name = sys.argv[2]
    gid = sys.argv[3]

    return path, galaxy_user_name, gid


def main():
    path, galaxy_user_name, gid = validate_paramters()
    os.system('chown -Rh %s %s' % (galaxy_user_name, path))
    os.system('chgrp -Rh %s %s' % (gid, path))


if __name__ == "__main__":
    main()
