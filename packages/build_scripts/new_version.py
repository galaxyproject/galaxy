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


def _project_version_file(project_directory):
    # Prefer pyproject.toml; support setup.cfg for release branches that use it.
    for name in ("pyproject.toml", "setup.cfg"):
        path = os.path.join(project_directory, name)
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"No pyproject.toml or setup.cfg found in {project_directory}")


def _set_version(text, new_version):
    # Preserve the manifest's version quoting.
    def repl(match):
        quote = match.group(1)
        return f"version = {quote}{new_version}{quote}"

    return re.sub(r'^version\s*=\s*("?).*', repl, text, count=1, flags=re.MULTILINE)


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

    project_file = _project_version_file(PROJECT_DIRECTORY)
    with open(project_file) as f:
        project_metadata = f.read()
    if not DEV_RELEASE:
        new_version = f"{new_version}.dev0"
    project_metadata = _set_version(project_metadata, new_version)
    with open(project_file, "w") as f:
        f.write(project_metadata)
    shell(["git", "commit", "-m", f"Starting work on {PROJECT_NAME} {new_version}", "HISTORY.rst", project_file])


def shell(cmds, **kwds):
    p = subprocess.Popen(cmds, **kwds)
    return p.wait()


if __name__ == "__main__":
    main(sys.argv)
