#!/usr/bin/env python
"""A simple script to redirect stderr to stdout when the return code is zero.

See https://bitbucket.org/galaxy/galaxy-central/issue/325/

Currently Galaxy ignores the return code from command line tools (even if it
is non-zero which by convention indicates an error) and treats any output on
stderr as an error (even though by convention stderr is used for errors or
warnings).

This script runs the given command line, capturing all stdout and stderr in
memory, and gets the return code. For a zero return code, any stderr (which
should be warnings only) is added to the stdout. That way Galaxy believes
everything is fine. For a non-zero return code, we output stdout as is, and
any stderr, plus the return code to ensure there is some output on stderr.
That way Galaxy treats this as an error.

Once issue 325 is fixed, this script will not be needed.
"""
import sys
import subprocess

#Avoid using shell=True when we call subprocess to ensure if the Python
#script is killed, so too is the BLAST process.
try:
    words = []
    for w in sys.argv[1:]:
       if " " in w:
           words.append('"%s"' % w)
       else:
           words.append(w)
    cmd = " ".join(words)
    child = subprocess.Popen(sys.argv[1:],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
except Exception, err:
    sys.stderr.write("Error invoking command:\n%s\n\n%s\n" % (cmd, err))
    sys.exit(1)
#Use .communicate as can get deadlocks with .wait(),
stdout, stderr = child.communicate()
return_code = child.returncode

if return_code:
    sys.stdout.write(stdout)
    # Galaxy seems to hang with large stderr (20000 char fails)
    max_stderr_len = 15000
    if len(stderr) > max_stderr_len:
        stderr_trunc = "%s\n\n... (truncated to reduce size) ...\n\n%s\n" % (stderr[:max_stderr_len/2],
                                          stderr[-max_stderr_len/2:])
    else:
        stderr_trunc = stderr
    sys.stderr.write(stderr_trunc)
    sys.stderr.write("Return error code %i from command:\n" % return_code)
    sys.stderr.write("%s\n" % cmd)
else:
    sys.stdout.write(stdout)
    sys.stdout.write(stderr)
