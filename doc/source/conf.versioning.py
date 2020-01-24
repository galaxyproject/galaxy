# -*- coding: utf-8 -*-
#
# Galaxy sphinxcontrib-simpleversioning documentation build configuration file
#
# This file is written to the end of conf.py by Jenkins
#

from distutils.version import LooseVersion
from subprocess import check_output

# This is set in the Jenkins matrix config
TARGET_GIT_BRANCH = os.environ.get('TARGET_GIT_BRANCH', 'dev')  # noqa: F821

# Version message templates
OLD_BANNER = """This document is for an old release of Galaxy."""
DEV_BANNER = """This document is for an in-development version of Galaxy."""
PRE_BANNER = """This document is for a pre-release version of Galaxy."""
BANNER_APPEND = """ You can alternatively <a href="%(stable_path)s">view this page in the latest release if it
exists</a> or <a href="%(stable_root)s">view the top of the latest release's documentation</a>."""

# Minimum version for linking to docs
MIN_DOC_VERSION = LooseVersion('17.05')

# Enable simpleversioning
extensions += ['sphinxcontrib.simpleversioning']  # noqa: F821

# -- sphinxcontrib-simpleversioning Settings ---------------------------------

simpleversioning_path_template = '/en/{version}/{pagename}'
simpleversioning_stable_version = 'master'
simpleversioning_current_version = TARGET_GIT_BRANCH
simpleversioning_versions = [
    {'id': 'master', 'name': 'stable'},
    # Additional versions added below
]

# Used for determining the latest stable release so the banner can be added to older releases.
_stable = None

_target_ver = None
_pre_release = False
if TARGET_GIT_BRANCH.startswith('release_'):
    _target_ver = TARGET_GIT_BRANCH[len('release_'):]

# Use tags to determine versions - a stable version will have a branch before it's released, but not a tag.
for _tag in reversed(check_output(('git', 'tag')).splitlines()):
    if _tag.startswith('v') and _tag.count('.') == 1:
        # this version is released
        _ver = _tag[1:]
        if not _stable:
            _stable = _ver
            if _target_ver and LooseVersion(_target_ver) > LooseVersion(_ver):
                # Pre-release
                simpleversioning_versions.append(
                    {'id': TARGET_GIT_BRANCH, 'name': _target_ver}
                )
                _pre_release = True
        if LooseVersion(_ver) >= MIN_DOC_VERSION:
            simpleversioning_versions.append(
                {'id': 'release_%s' % _ver, 'name': _ver}
            )

simpleversioning_versions.append(
    {'id': 'latest', 'name': 'dev'},
)

if TARGET_GIT_BRANCH.startswith('release_'):
    # The current stable release will go here but fail the next conditional, avoiding either banner.
    if TARGET_GIT_BRANCH != 'release_%s' % _stable:
        simpleversioning_show_banner = True
        if _pre_release:
            simpleversioning_banner_message = PRE_BANNER + BANNER_APPEND
        else:
            simpleversioning_banner_message = OLD_BANNER + BANNER_APPEND
elif TARGET_GIT_BRANCH != 'master':
    simpleversioning_show_banner = True
    simpleversioning_banner_message = DEV_BANNER + BANNER_APPEND
