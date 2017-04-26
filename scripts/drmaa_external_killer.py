#!/usr/bin/env python

"""
Terminates a DRMAA job if given a job id and (appropriate) user id.
"""

import errno
import os
import pwd
import sys

import drmaa


def validate_paramters():
    if len(sys.argv) < 3:
        sys.stderr.write("usage: %s [job ID] [user uid]\n" % sys.argv[0])
        exit(1)

    jobID = sys.argv[1]
    uid = int(sys.argv[2])
    return jobID, uid


def set_user(uid):
    try:
        gid = pwd.getpwuid(uid).pw_gid
        os.setgid(gid)
        os.setuid(uid)
    except OSError as e:
        if e.errno == errno.EPERM:
            sys.stderr.write("error: setuid(%d) failed: permission denied. Did you setup 'sudo' correctly for this script?\n" % uid )
            exit(1)
        else:
            pass
    if os.getuid() == 0:
        sys.stderr.write("error: UID is 0 (root) after changing user. This script should not be run as root. aborting.\n" )
        exit(1)
    if os.geteuid() == 0:
        sys.stderr.write("error: EUID is 0 (root) after changing user. This script should not be run as root. aborting.\n" )
        exit(1)


def main():
    jobID, uid = validate_paramters()
    set_user(uid)
    s = drmaa.Session()
    s.initialize()
    s.control(jobID, drmaa.JobControlAction.TERMINATE)
    s.exit()


if __name__ == "__main__":
    main()
