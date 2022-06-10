import os
import re
from distutils.version import LooseVersion

_version_re = re.compile(r"^version\s+=\s+(.*)", flags=re.MULTILINE)


def main():
    DEV_RELEASE = os.environ.get("DEV_RELEASE", None) == "1"
    PROJECT_DIRECTORY = os.getcwd()

    setup_cfg_path = os.path.join(PROJECT_DIRECTORY, "setup.cfg")

    with open(setup_cfg_path) as f:
        setup_cfg = f.read()
    version_match = _version_re.search(setup_cfg)
    assert version_match
    version = version_match.group(1)

    if not DEV_RELEASE:
        # Strip .devN
        version_tuple = LooseVersion(version).version[0:3]
        print(".".join(map(str, version_tuple)))
    else:
        print(version)


if __name__ == "__main__":
    main()
