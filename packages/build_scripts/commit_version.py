#!/usr/bin/env python
# Modify version...
import datetime
import os
import re
import subprocess
import sys


def main(argv):
    DEV_RELEASE = os.environ.get("DEV_RELEASE", None) == "1"
    PROJECT_DIRECTORY = os.getcwd()
    PROJECT_DIRECTORY_NAME = os.path.basename(os.path.abspath(PROJECT_DIRECTORY))
    PROJECT_MODULE_FILENAME = f"project_galaxy_{PROJECT_DIRECTORY_NAME}.py"
    PROJECT_NAME = PROJECT_DIRECTORY_NAME.replace("_", "-")

    source_dir = argv[1]
    version = argv[2]
    mod_path = os.path.join(PROJECT_DIRECTORY, source_dir, PROJECT_MODULE_FILENAME)
    if not DEV_RELEASE:
        history_path = os.path.join(PROJECT_DIRECTORY, "HISTORY.rst")
        with open(history_path) as f:
            history = f.read()
        today = datetime.datetime.today()
        today_str = today.strftime("%Y-%m-%d")
        history = history.replace(".dev0", f" ({today_str})")
        with open(history_path, "w") as f:
            f.write(history)
        with open(mod_path) as f:
            mod = f.read()
        mod = re.sub(r"__version__ = '[\d\.]*\.dev\d+'", f"__version__ = '{version}'", mod)
        with open(mod_path, "w") as f:
            f.write(mod)
    tag = f"galaxy-{PROJECT_NAME}-{version}"
    shell(["git", "commit", "-m", f"Version {version} of {PROJECT_NAME} (tag {tag}).", "HISTORY.rst", mod_path])
    shell(["git", "tag", tag])


def shell(cmds, **kwds):
    p = subprocess.Popen(cmds, **kwds)
    return p.wait()


if __name__ == "__main__":
    main(sys.argv)
