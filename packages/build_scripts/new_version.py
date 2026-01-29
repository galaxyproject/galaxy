#!/usr/bin/env python
# Modify version...
import os
import re
import subprocess
import sys

from packaging.version import Version

DEV_RELEASE = os.environ.get("DEV_RELEASE", None) == "1"
PROJECT_DIRECTORY = os.getcwd()
PROJECT_DIRECTORY_NAME = os.path.basename(os.path.abspath(PROJECT_DIRECTORY))
PROJECT_NAME = PROJECT_DIRECTORY_NAME.replace("_", "-")


def main(argv):
    version = argv[1]
    version_obj = Version(version)
    if not DEV_RELEASE:
        # Discard epoch, release numbers after micro, pre-, post-, dev-release segments and local version
        new_version_tuple = list(version_obj.release[:3])
        if len(new_version_tuple) < 3:
            new_version_tuple.append(0)
        else:
            new_version_tuple[2] += 1
        new_version = ".".join(map(str, new_version_tuple))
    else:
        dev_number = version_obj.dev
        assert dev_number is not None
        new_version = f"{version_obj.base_version}.dev{dev_number + 1}"

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
        setup_cfg = re.sub(r"^version = .*$", f"version = {new_version}.dev0", setup_cfg, count=1, flags=re.MULTILINE)
    else:
        setup_cfg = re.sub(
            r"^version = .*$",
            rf"version = {new_version}",
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
