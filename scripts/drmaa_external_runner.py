#!/usr/bin/env python

"""
Submit a DRMAA job given a user id and a job template file (in JSON format)
defining any or all of the following: args, remoteCommand, outputPath,
errorPath, nativeSpecification, name, email, project
"""

import errno
import json
import os
import pwd
import sys

import drmaa

DRMAA_jobTemplate_attributes = [
    "args",
    "remoteCommand",
    "outputPath",
    "errorPath",
    "nativeSpecification",
    "workingDirectory",
    "jobName",
    "email",
    "project",
]


def load_job_template(jt, data):
    for attr in DRMAA_jobTemplate_attributes:
        if attr in data:
            setattr(jt, attr, data[attr])


def valid_numeric_userid(userid):
    try:
        uid = int(userid)
    except ValueError:
        return False
    try:
        pwd.getpwuid(uid)
    except KeyError:
        sys.stderr.write(f"error: User-ID ({uid}) is not valid.\n")
        exit(1)
    return True


def get_user_id_by_name(username):
    try:
        pw = pwd.getpwnam(username)
    except KeyError:
        sys.stderr.write(f"error: User name ({username}) is not valid.\n")
        exit(1)
    return pw.pw_uid


def json_file_exists(json_filename):
    if not os.path.exists(json_filename):
        sys.stderr.write(f"error: JobTemplate file ({json_filename}) doesn't exist\n")
        exit(1)

    return True


def validate_parameters():
    assign_all_groups = False
    if "--assign_all_groups" in sys.argv:
        assign_all_groups = True
        sys.argv.remove("--assign_all_groups")

    if len(sys.argv) < 3:
        sys.stderr.write(f"usage: {sys.argv[0]} [USER-ID] [JSON-JOB-TEMPLATE-FILE]\n")
        exit(1)

    userid = sys.argv[1]
    json_filename = sys.argv[2]

    if valid_numeric_userid(userid):
        uid = int(userid)
    else:
        uid = get_user_id_by_name(userid)

    if uid == 0:
        sys.stderr.write("error: userid must not be 0 (root)\n")
        exit(1)

    return uid, json_filename, assign_all_groups


def set_user(uid: int, assign_all_groups: bool):
    try:
        # Get user's default group and set it to current process to make sure
        # file permissions are inherited correctly
        # Solves issue with permission denied for JSON files
        gid = pwd.getpwuid(uid).pw_gid
        import grp

        os.setgid(gid)
        if assign_all_groups:
            # Added lines to assure read/write permission for groups
            user = pwd.getpwuid(uid).pw_name
            groups = [g.gr_gid for g in grp.getgrall() if user in g.gr_mem]

            os.setgroups(groups)
        os.setuid(uid)

    except OSError as e:
        if e.errno == errno.EPERM:
            sys.stderr.write(
                f"error: setuid({uid}) failed: permission denied. Did you setup 'sudo' correctly for this script?\n"
            )
            exit(1)
        else:
            pass

    if os.getuid() == 0:
        sys.stderr.write(
            "error: UID is 0 (root) after changing user. This script should not be run as root. aborting.\n"
        )
        exit(1)

    if os.geteuid() == 0:
        sys.stderr.write(
            "error: EUID is 0 (root) after changing user. This script should not be run as root. aborting.\n"
        )
        exit(1)


def main():
    userid, json_filename, assign_all_groups = validate_parameters()
    # load JSON job template data
    json_file_exists(json_filename)
    with open(json_filename) as f:
        data = json.load(f)
    set_user(userid, assign_all_groups)
    # Added to disable LSF generated messages that would interfer with this
    # script. Fix thank to Chong Chen at IBM.
    os.environ["BSUB_QUIET"] = "Y"
    s = drmaa.Session()
    s.initialize()
    jt = s.createJobTemplate()
    load_job_template(jt, data)
    # runJob will raise if there's a submittion error
    jobId = s.runJob(jt)
    s.deleteJobTemplate(jt)
    s.exit()

    # Print the Job-ID and exit. Galaxy will pick it up from there.
    print(jobId)


if __name__ == "__main__":
    main()
