# -*- coding: utf-8 -*-
#
# Galaxy sphinxcontrib-simpleversioning documentation build configuration file
#
# This file is written to the end of conf.py by Jenkins
#

import os
from distutils.version import LooseVersion
from subprocess import check_output
# This is set by the Jenkins Git Plugin
GIT_BRANCH = os.environ.get('GIT_BRANCH')

# Version message templates
OLD_BANNER = """This document is for an old release of Galaxy. You can alternatively <a href="%(stable_path)s">view this
page in the latest release if it exists</a> or <a href="%(stable_root)s">view the top of the latest release's
documentation</a>."""
DEV_BANNER = """This document is for an in-development version of Galaxy. You can alternatively <a
href="%(stable_path)s">view this page in the latest release if it exists</a> or <a href="%(stable_root)s">view the top
of the latest release's documentation</a>."""

# Minimum version for linking to docs
MIN_DOC_VERSION = LooseVersion('17.05')

# Enable simpleversioning
if GIT_BRANCH:
    extensions += ['sphinxcontrib.simpleversioning']

# -- sphinxcontrib-simpleversioning Settings ---------------------------------

simpleversioning_path_template = '/en/{version}/{pagename}'
simpleversioning_stable_version = 'master'

if GIT_BRANCH:

    _stable = None
    _branch = GIT_BRANCH.rsplit('/', 1)[-1]

    simpleversioning_versions = [
        {'id': 'master', 'name': 'stable'},
    ]

    for _tag in reversed(check_output(('git', 'tag')).splitlines()):
        if _tag.startswith('v') and _tag.count('.') == 1:
            # this version is released
            _tag = _tag[1:]
            if not _stable:
                _stable = _tag
            if LooseVersion(_tag) >= MIN_DOC_VERSION:
                simpleversioning_versions.append(
                    {'id': 'release_%s' % _tag[1:], 'name': _tag}
                )

    simpleversioning_versions.append(
        {'id': 'latest', 'name': 'dev'},
    )

    simpleversioning_current_version = _branch
    if _branch == 'master':
        pass  # avoid the else
    elif _branch == 'release_%s' % _stable:
        simpleversioning_current_version = _stable
    elif _branch.startswith('release_'):
        simpleversioning_current_version = _branch[len('release_'):]
        simpleversioning_show_banner = True
        simpleversioning_banner_message = OLD_BANNER
    else:
        simpleversioning_current_version = 'latest'
        simpleversioning_show_banner = True
        simpleversioning_banner_message = DEV_BANNER
