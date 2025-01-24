#
# Galaxy sphinxcontrib-simpleversioning documentation build configuration file
# This file is appended to conf.py by the Build docs github workflow.
#
import re
from subprocess import check_output

from packaging.version import Version

# This is set in the Jenkins matrix config
TARGET_GIT_BRANCH = os.environ.get("TARGET_BRANCH", "dev")  # noqa: F821

# Version message templates
OLD_BANNER = """This document is for an old release of Galaxy."""
DEV_BANNER = """This document is for an in-development version of Galaxy."""
PRE_BANNER = """This document is for a pre-release version of Galaxy."""
BANNER_APPEND = """ You can alternatively <a href="%(stable_path)s">view this page in the latest release if it
exists</a> or <a href="%(stable_root)s">view the top of the latest release's documentation</a>."""

# Minimum version for linking to docs
MIN_DOC_VERSION = Version("17.05")

# Enable simpleversioning
extensions += ["sphinxcontrib.simpleversioning"]  # noqa: F821

# -- sphinxcontrib-simpleversioning Settings ---------------------------------

simpleversioning_path_template = "/en/{version}/{pagename}"
simpleversioning_stable_version = "master"
simpleversioning_current_version = TARGET_GIT_BRANCH
simpleversioning_versions = [
    {"id": "latest", "name": "dev"},
    {"id": "master", "name": "stable"},
    # Additional versions added below
]

# Used for determining the latest stable release so the banner can be added to older releases.
_stable = None
# Use tags to determine versions - a stable version will have a branch before it's released, but not a tag.
tags = check_output(("git", "tag")).decode().splitlines()
for _tag in reversed(tags):
    if _tag.startswith("v") and _tag.count(".") == 1:
        # this version is released
        _ver = _tag[1:]
        if not _stable:
            _stable = _ver
        if Version(_ver) >= MIN_DOC_VERSION:
            simpleversioning_versions.append({"id": f"release_{_ver}", "name": _ver})

if re.fullmatch(r"release_\d{2}\.\d{1,2}", TARGET_GIT_BRANCH):
    if _stable:
        # The current stable release will go here but fail the next conditional, avoiding either banner.
        if TARGET_GIT_BRANCH != f"release_{_stable}":
            simpleversioning_show_banner = True
            _target_ver = TARGET_GIT_BRANCH[len("release_") :]
            if Version(_target_ver) > Version(_stable):
                # Pre-release
                # Insert it between master and _stable
                simpleversioning_versions.insert(2, {"id": TARGET_GIT_BRANCH, "name": _target_ver})
                simpleversioning_banner_message = PRE_BANNER + BANNER_APPEND
            else:
                simpleversioning_banner_message = OLD_BANNER + BANNER_APPEND
elif TARGET_GIT_BRANCH != "master":
    if TARGET_GIT_BRANCH != "dev":
        # Feature branch
        simpleversioning_versions.append({"id": TARGET_GIT_BRANCH, "name": TARGET_GIT_BRANCH})
    simpleversioning_show_banner = True
    simpleversioning_banner_message = DEV_BANNER + BANNER_APPEND
