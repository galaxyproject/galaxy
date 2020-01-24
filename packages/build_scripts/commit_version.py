#!/usr/bin/env python
# Modify version...
import datetime
import os
import re
import subprocess
import sys


DEV_RELEASE = os.environ.get("DEV_RELEASE", None) == "1"
PROJECT_DIRECTORY = os.getcwd()
PROJECT_DIRECTORY_NAME = os.path.basename(os.path.abspath(PROJECT_DIRECTORY))
PROJECT_MODULE_FILENAME = "project_galaxy_%s.py" % PROJECT_DIRECTORY_NAME
PROJECT_NAME = PROJECT_DIRECTORY_NAME.replace("_", "-")


def main(argv):
    source_dir = argv[1]
    version = argv[2]
    mod_path = os.path.join(PROJECT_DIRECTORY, source_dir, PROJECT_MODULE_FILENAME)
    if not DEV_RELEASE:
        history_path = os.path.join(PROJECT_DIRECTORY, "HISTORY.rst")
        history = open(history_path, "r").read()
        today = datetime.datetime.today()
        today_str = today.strftime('%Y-%m-%d')
        history = history.replace(".dev0", " (%s)" % today_str)
        open(history_path, "w").write(history)
        mod = open(mod_path, "r").read()
        mod = re.sub(r"__version__ = '[\d\.]*\.dev\d+'",
                    "__version__ = '%s'" % version,
                    mod)
        mod = open(mod_path, "w").write(mod)
    tag = "galaxy-%s-%s" % (PROJECT_NAME, version)
    shell(["git", "commit", "-m", "Version %s of %s (tag %s)." % (version, PROJECT_NAME, tag),
           "HISTORY.rst", mod_path])
    shell(["git", "tag", tag])


def shell(cmds, **kwds):
    p = subprocess.Popen(cmds, **kwds)
    return p.wait()


if __name__ == "__main__":
    main(sys.argv)
