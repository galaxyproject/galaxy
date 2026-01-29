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
    PROJECT_NAME = PROJECT_DIRECTORY_NAME.replace("_", "-")

    version = argv[1]
    setup_cfg_path = os.path.join(PROJECT_DIRECTORY, "setup.cfg")

    if not DEV_RELEASE:
        history_path = os.path.join(PROJECT_DIRECTORY, "HISTORY.rst")
        with open(history_path) as f:
            history = f.read()
        today = datetime.datetime.today()
        today_str = today.strftime("%Y-%m-%d")
        history = history.replace(".dev0", f" ({today_str})")
        with open(history_path, "w") as f:
            f.write(history)
        with open(setup_cfg_path) as f:
            setup_cfg = f.read()
        setup_cfg = re.sub(
            r"^version = [\d\.]+\.dev\d+", f"version = {version}", setup_cfg, count=1, flags=re.MULTILINE
        )
        with open(setup_cfg_path, "w") as f:
            f.write(setup_cfg)
    tag = f"galaxy-{PROJECT_NAME}-{version}"
    shell(["git", "commit", "-m", f"Version {version} of {PROJECT_NAME} (tag {tag}).", "HISTORY.rst", setup_cfg_path])
    shell(["git", "tag", tag])


def shell(cmds, **kwds):
    p = subprocess.Popen(cmds, **kwds)
    return p.wait()


if __name__ == "__main__":
    main(sys.argv)
