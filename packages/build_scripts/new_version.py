#!/usr/bin/env python
# Modify version...
import os
import re
import subprocess
import sys
from distutils.version import StrictVersion

DEV_RELEASE = os.environ.get("DEV_RELEASE", None) == "1"
PROJECT_DIRECTORY = os.getcwd()
PROJECT_DIRECTORY_NAME = os.path.basename(os.path.abspath(PROJECT_DIRECTORY))
PROJECT_NAME = PROJECT_DIRECTORY_NAME.replace("_", "-")


def main(argv):
    version = argv[1]
    if not DEV_RELEASE:
        old_version = StrictVersion(version)
        old_version_tuple = old_version.version
        new_version_tuple = list(old_version_tuple)
        new_version_tuple[2] = old_version_tuple[2] + 1
        new_version = ".".join(map(str, new_version_tuple))
        new_dev_version = 0
    else:
        dev_match = re.compile(r"dev([\d]+)").search(version)
        assert dev_match
        dev_version = dev_match.group(1)
        new_dev_version = int(dev_version) + 1
        new_version = version.replace(f"dev{dev_version}", f"dev{new_dev_version}")

    history_path = os.path.join(PROJECT_DIRECTORY, "HISTORY.rst")
    if not DEV_RELEASE:
        with open(history_path) as f:
            history = f.read()

        def extend(from_str, line):
            from_str += "\n"
            return history.replace(from_str, from_str + line + "\n")

        history = extend(
            ".. to_doc",
            f"""
---------------------
{new_version}.dev0
---------------------

""",
        )
        with open(history_path, "w") as f:
            f.write(history)

    setup_cfg_path = os.path.join(PROJECT_DIRECTORY, "setup.cfg")
    with open(setup_cfg_path) as f:
        setup_cfg = f.read()
    if not DEV_RELEASE:
        setup_cfg = re.sub(
            r"^version = [\d\.]+", f"version = {new_version}.dev0", setup_cfg, count=1, flags=re.MULTILINE
        )
    else:
        setup_cfg = re.sub(
            rf"^version = ([\d\.]+).dev{dev_version}",
            rf"version = \1.dev{new_dev_version}",
            setup_cfg,
            count=1,
            flags=re.MULTILINE,
        )
    with open(setup_cfg_path, "w") as f:
        f.write(setup_cfg)
    shell(["git", "commit", "-m", f"Starting work on {PROJECT_NAME} {new_version}", "HISTORY.rst", setup_cfg_path])


def shell(cmds, **kwds):
    p = subprocess.Popen(cmds, **kwds)
    return p.wait()


if __name__ == "__main__":
    main(sys.argv)
