import os
import re

from packaging.version import Version

_version_re = re.compile(r"^version\s*=\s*\"?([^\"\s]+)\"?", flags=re.MULTILINE)


def _project_version_file(project_directory):
    # pyproject.toml is canonical after the setup.cfg -> pyproject.toml migration;
    # setup.cfg is kept as a fallback for packages that have not migrated yet.
    for name in ("pyproject.toml", "setup.cfg"):
        path = os.path.join(project_directory, name)
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"No pyproject.toml or setup.cfg found in {project_directory}")


def main():
    DEV_RELEASE = os.environ.get("DEV_RELEASE", None) == "1"
    PROJECT_DIRECTORY = os.getcwd()

    with open(_project_version_file(PROJECT_DIRECTORY)) as f:
        project_metadata = f.read()
    version_match = _version_re.search(project_metadata)
    assert version_match
    version = version_match.group(1)

    if not DEV_RELEASE:
        version_obj = Version(version)
        # Strip .devN
        print(version_obj.base_version)
    else:
        print(version)


if __name__ == "__main__":
    main()
