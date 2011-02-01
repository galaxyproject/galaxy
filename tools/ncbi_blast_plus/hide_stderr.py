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

#Sadly passing the list directly to subprocess didn't seem to work.
words = []
for w in sys.argv[1:]:
    if " " in w:
        words.append('"%s"' % w)
    else:
        words.append(w)
cmd = " ".join(words)
child = subprocess.Popen(cmd, shell=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#Use .communicate as can get deadlocks with .wait(),
stdout, stderr = child.communicate()
return_code = child.returncode

if return_code:
    sys.stdout.write(stdout)
    sys.stderr.write(stderr)
    sys.stderr.write("Return error code %i from command:\n" % return_code)
    sys.stderr.write("%s\n" % cmd)
else:
    sys.stdout.write(stdout)
    sys.stdout.write(stderr)
