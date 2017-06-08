"""Utilities for working with mulled abstractions outside the mulled package."""
from __future__ import print_function

import collections
import hashlib

from distutils.version import LooseVersion

try:
    import requests
except ImportError:
    requests = None


def create_repository(namespace, repo_name, oauth_token):
    assert oauth_token
    headers = {'Authorization': 'Bearer %s' % oauth_token}
    data = {
        "repository": repo_name,
        "namespace": namespace,
        "description": "",
        "visibility": "public",
    }
    requests.post("https://quay.io/api/v1/repository", json=data, headers=headers)


def quay_versions(namespace, pkg_name):
    """Get all version tags for a Docker image stored on quay.io for supplied package name."""
    data = quay_repository(namespace, pkg_name)

    if 'error_type' in data and data['error_type'] == "invalid_token":
        return []

    if 'tags' not in data:
        raise Exception("Unexpected response from quay.io - not tags description found [%s]" % data)

    return [tag for tag in data['tags'] if tag != 'latest']


def quay_repository(namespace, pkg_name):
    if requests is None:
        raise Exception("requets library is unavailable, functionality not available.")

    assert namespace is not None
    assert pkg_name is not None
    url = 'https://quay.io/api/v1/repository/%s/%s' % (namespace, pkg_name)
    response = requests.get(url, timeout=None)
    data = response.json()
    return data


def mulled_tags_for(namespace, image, tag_prefix=None):
    """Fetch remote tags available for supplied image name.

    The result will be sorted so newest tags are first.
    """
    tags = quay_versions(namespace, image)
    if tag_prefix is not None:
        tags = [t for t in tags if t.startswith(tag_prefix)]
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


def _simple_image_name(targets, image_build=None):
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


def v1_image_name(targets, image_build=None, name_override=None):
    """Generate mulled hash version 1 container identifier for supplied arguments.

    If a single target is specified, simply use the supplied name and version as
    the repository name and tag respectively. If multiple targets are supplied,
    hash the package names and versions together as the repository name. For mulled
    version 1 containers the image build is the repository tag (if supplied).

    >>> single_targets = [build_target("samtools", version="1.3.1")]
    >>> v1_image_name(single_targets)
    'samtools:1.3.1'
    >>> multi_targets = [build_target("samtools", version="1.3.1"), build_target("bwa", version="0.7.13")]
    >>> v1_image_name(multi_targets)
    'mulled-v1-b06ecbd9141f0dbbc0c287375fc0813adfcbdfbd'
    >>> multi_targets_on_versionless = [build_target("samtools", version="1.3.1"), build_target("bwa")]
    >>> v1_image_name(multi_targets_on_versionless)
    'mulled-v1-bda945976caa5734347fbf7f35066d9f58519e0c'
    >>> multi_targets_versionless = [build_target("samtools"), build_target("bwa")]
    >>> v1_image_name(multi_targets_versionless)
    'mulled-v1-fe8faa35dbf6dc65a0f7f5d4ea12e31a79f73e40'
    """
    if name_override is not None:
        print("WARNING: Overriding mulled image name, auto-detection of 'mulled' package attributes will fail to detect result.")
        return name_override

    targets = list(targets)
    if len(targets) == 1:
        return _simple_image_name(targets, image_build=image_build)
    else:
        targets_order = sorted(targets, key=lambda t: t.package_name)
        requirements_buffer = "\n".join(map(conda_build_target_str, targets_order))
        m = hashlib.sha1()
        m.update(requirements_buffer.encode())
        suffix = "" if not image_build else ":%s" % image_build
        return "mulled-v1-%s%s" % (m.hexdigest(), suffix)


def v2_image_name(targets, image_build=None, name_override=None):
    """Generate mulled hash version 2 container identifier for supplied arguments.

    If a single target is specified, simply use the supplied name and version as
    the repository name and tag respectively. If multiple targets are supplied,
    hash the package names as the repository name and hash the package versions (if set)
    as the tag.

    >>> single_targets = [build_target("samtools", version="1.3.1")]
    >>> v2_image_name(single_targets)
    'samtools:1.3.1'
    >>> multi_targets = [build_target("samtools", version="1.3.1"), build_target("bwa", version="0.7.13")]
    >>> v2_image_name(multi_targets)
    'mulled-v2-fe8faa35dbf6dc65a0f7f5d4ea12e31a79f73e40:4d0535c94ef45be8459f429561f0894c3fe0ebcf'
    >>> multi_targets_on_versionless = [build_target("samtools", version="1.3.1"), build_target("bwa")]
    >>> v2_image_name(multi_targets_on_versionless)
    'mulled-v2-fe8faa35dbf6dc65a0f7f5d4ea12e31a79f73e40:b0c847e4fb89c343b04036e33b2daa19c4152cf5'
    >>> multi_targets_versionless = [build_target("samtools"), build_target("bwa")]
    >>> v2_image_name(multi_targets_versionless)
    'mulled-v2-fe8faa35dbf6dc65a0f7f5d4ea12e31a79f73e40'
    """
    if name_override is not None:
        print("WARNING: Overriding mulled image name, auto-detection of 'mulled' package attributes will fail to detect result.")
        return name_override

    targets = list(targets)
    if len(targets) == 1:
        return _simple_image_name(targets, image_build=image_build)
    else:
        targets_order = sorted(targets, key=lambda t: t.package_name)
        package_name_buffer = "\n".join(map(lambda t: t.package_name, targets_order))
        package_hash = hashlib.sha1()
        package_hash.update(package_name_buffer.encode())

        versions = map(lambda t: t.version, targets_order)
        if any(versions):
            # Only hash versions if at least one package has versions...
            version_name_buffer = "\n".join(map(lambda t: t.version or "null", targets_order))
            version_hash = hashlib.sha1()
            version_hash.update(version_name_buffer.encode())
            version_hash_str = version_hash.hexdigest()
        else:
            version_hash_str = ""

        if not image_build:
            build_suffix = ""
        elif version_hash_str:
            # tagged verson is <version_hash>-<build>
            build_suffix = "-%s" % image_build
        else:
            # tagged version is simply the build
            build_suffix = image_build
        suffix = ""
        if version_hash_str or build_suffix:
            suffix = ":%s%s" % (version_hash_str, build_suffix)
        return "mulled-v2-%s%s" % (package_hash.hexdigest(), suffix)


image_name = v1_image_name  # deprecated

__all__ = (
    "build_target",
    "conda_build_target_str",
    "image_name",
    "mulled_tags_for",
    "quay_versions",
    "split_tag",
    "Target",
    "v1_image_name",
    "v2_image_name",
    "version_sorted",
)
