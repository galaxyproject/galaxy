#!/usr/bin/env python
# Modify version...
import datetime
import os
import re
import subprocess
import sys


def _project_version_file(project_directory):
    # pyproject.toml is canonical after the setup.cfg -> pyproject.toml migration;
    # setup.cfg is kept as a fallback for packages that have not migrated yet.
    for name in ("pyproject.toml", "setup.cfg"):
        path = os.path.join(project_directory, name)
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"No pyproject.toml or setup.cfg found in {project_directory}")


def _set_version(text, pattern, new_version):
    # Preserve the existing quoting style (pyproject.toml quotes the version,
    # legacy setup.cfg did not).
    def repl(match):
        quote = match.group(1)
        return f"version = {quote}{new_version}{quote}"

    return re.sub(pattern, repl, text, count=1, flags=re.MULTILINE)


def main(argv):
    DEV_RELEASE = os.environ.get("DEV_RELEASE", None) == "1"
    PROJECT_DIRECTORY = os.getcwd()
    PROJECT_DIRECTORY_NAME = os.path.basename(os.path.abspath(PROJECT_DIRECTORY))
    PROJECT_NAME = PROJECT_DIRECTORY_NAME.replace("_", "-")

    version = argv[1]
    project_file = _project_version_file(PROJECT_DIRECTORY)

    if not DEV_RELEASE:
        history_path = os.path.join(PROJECT_DIRECTORY, "HISTORY.rst")
        with open(history_path) as f:
            history = f.read()
        today = datetime.datetime.today()
        today_str = today.strftime("%Y-%m-%d")
        history = history.replace(".dev0", f" ({today_str})")
        with open(history_path, "w") as f:
            f.write(history)
        with open(project_file) as f:
            project_metadata = f.read()
        project_metadata = _set_version(
            project_metadata,
            r'^version\s*=\s*("?)[\d.]+\.dev\d+"?',
            version,
        )
        with open(project_file, "w") as f:
            f.write(project_metadata)
    tag = f"galaxy-{PROJECT_NAME}-{version}"
    shell(["git", "commit", "-m", f"Version {version} of {PROJECT_NAME} (tag {tag}).", "HISTORY.rst", project_file])
    shell(["git", "tag", tag])


def shell(cmds, **kwds):
    p = subprocess.Popen(cmds, **kwds)
    return p.wait()


if __name__ == "__main__":
    main(sys.argv)
