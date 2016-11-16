"""Utilities for working with mulled abstractions outside the mulled package."""
from __future__ import print_function

import collections
import hashlib

from distutils.version import LooseVersion

try:
    import requests
except ImportError:
    requests = None


def quay_versions(namespace, pkg_name):
    """Get all version tags for a Docker image stored on quay.io for supplied package name."""
    if requests is None:
        raise Exception("requets library is unavailable, functionality not available.")

    assert namespace is not None
    assert pkg_name is not None
    url = 'https://quay.io/api/v1/repository/%s/%s' % (namespace, pkg_name)
    response = requests.get(url, timeout=None)
    data = response.json()
    if 'error_type' in data and data['error_type'] == "invalid_token":
        return []

    if 'tags' not in data:
        raise Exception("Unexpected response from quay.io - not tags description found [%s]" % data)

    return [tag for tag in data['tags'] if tag != 'latest']


def mulled_tags_for(namespace, image):
    """Fetch remote tags available for supplied image name.

    The result will be sorted so newest tags are first.
    """
    tags = quay_versions(namespace, image)
    tags = version_sorted(tags)
    return tags


def split_tag(tag):
    """Split mulled image name into conda version and conda build."""
    version = tag.split('--', 1)[0]
    build = tag.split('--', 1)[1]
    return version, build


def version_sorted(elements):
    """Sort iterable based on loose description of "version" from newest to oldest."""
    return sorted(elements, key=LooseVersion, reverse=True)


Target = collections.namedtuple("Target", ["package_name", "version", "build"])


def build_target(package_name, version=None, build=None, tag=None):
    """Use supplied arguments to build a :class:`Target` object."""
    if tag is not None:
        assert version is None
        assert build is None
        version, build = split_tag(tag)

    return Target(package_name, version, build)


def conda_build_target_str(target):
    rval = target.package_name
    if target.version:
        rval += "=%s" % target.version

        if target.build:
            rval += "=%s" % target.build

    return rval


def image_name(targets, image_build=None, name_override=None):
    if name_override is not None:
        print("WARNING: Overriding mulled image name, auto-detection of 'mulled' package attributes will fail to detect result.")
        return name_override

    targets = list(targets)
    if len(targets) == 1:
        target = targets[0]
        suffix = ""
        if target.version is not None:
            if image_build is not None:
                print("WARNING: Hard-coding image build instead of using Conda build - this is not recommended.")
                suffix = image_build
            else:
                suffix += ":%s" % target.version
                build = target.build
                if build is not None:
                    suffix += "--%s" % build
        return "%s%s" % (target.package_name, suffix)
    else:
        targets_order = sorted(targets, key=lambda t: t.package_name)
        requirements_buffer = "\n".join(map(conda_build_target_str, targets_order))
        m = hashlib.sha1()
        m.update(requirements_buffer.encode())
        suffix = "" if not image_build else ":%s" % image_build
        return "mulled-v1-%s%s" % (m.hexdigest(), suffix)


__all__ = (
    "build_target",
    "conda_build_target_str",
    "image_name",
    "mulled_tags_for",
    "quay_versions",
    "split_tag",
    "Target",
    "version_sorted",
)
