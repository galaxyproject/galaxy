#!/usr/bin/env python
import os
import sys


def validate_paramters():
    if len(sys.argv) < 4:
        sys.stderr.write("usage: %s path user_name gid\n" % sys.argv[0])
        exit(1)

    path = sys.argv[1]
    galaxy_user_name = sys.argv[2]
    gid = sys.argv[3]

    return path, galaxy_user_name, gid


def main():
    path, galaxy_user_name, gid = validate_paramters()
    os.system('chown -Rh %s %s' % (galaxy_user_name, path))
    os.system('chgrp -Rh %s %s' % (gid, path))


if __name__ == "__main__":
    main()
