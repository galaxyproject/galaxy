#!/usr/bin/env python
import os
import sys
import errno
import pwd

#import simplejson as json
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

DRMAA_jobTemplate_attributes = [ 'args', 'remoteCommand', 'outputPath', 'errorPath', 'nativeSpecification',
                    'name','email','project' ]

def load_job_template_from_file(jt, filename):
    f = open(filename,'r')
    data = json.load(f)
    for attr in DRMAA_jobTemplate_attributes:
        if attr in data:
            setattr(jt, attr, data[attr])

def valid_numeric_userid(userid):
    try:
        uid = int(userid)
    except:
        return False
    try:
        pw = pwd.getpwuid(uid)
    except KeyError:
        sys.stderr.write("error: User-ID (%d) is not valid.\n" % uid)
        exit(1)
    return True

def get_user_id_by_name(username):
    try:
        pw = pwd.getpwnam(username)
    except KeyError:
        sys.stderr.write("error: User name (%s) is not valid.\n" % username)
        exit(1)
    return pw.pw_uid
def validate_paramters():
    if len(sys.argv)<3:
        sys.stderr.write("usage: %s [USER-ID] [JSON-JOB-TEMPLATE-FILE]\n" % sys.argv[0])
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

    if not os.path.exists(json_filename):
        sys.stderr.write("error: JobTemplate file (%s) doesn't exist\n" % ( json_filename ) )
        exit(1)

    return uid, json_filename

def set_user(uid):
    try:
        # Get user's default group and set it to current process to make sure file permissions are inherited correctly
        # Solves issue with permission denied for JSON files
        gid = pwd.getpwuid(uid).pw_gid
        os.setgid(gid)
        os.setuid(uid)
    except OSError, e:
        if e.errno == errno.EPERM:
            sys.stderr.write("error: setuid(%d) failed: permission denied. Did you setup 'sudo' correctly for this script?\n" % uid )
            exit(1)
        else:
            pass
    if os.getuid()==0:
        sys.stderr.write("error: UID is 0 (root) after changing user. This script should not be run as root. aborting.\n" )
        exit(1)
    if os.geteuid()==0:
        sys.stderr.write("error: EUID is 0 (root) after changing user. This script should not be run as root. aborting.\n" )
        exit(1)
def main():
    userid, json_filename = validate_paramters()
    set_user(userid)        
    s = drmaa.Session()
    s.initialize()
    jt = s.createJobTemplate()
    load_job_template_from_file(jt, json_filename)
    # runJob will raise if there's a submittion error
    jobId = s.runJob(jt)
    s.deleteJobTemplate(jt)
    s.exit()

    # Print the Job-ID and exit. Galaxy will pick it up from there.
    print jobId

if __name__ == "__main__":
    main()

