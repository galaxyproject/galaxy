"""This module describes the :class:`MulledContainerResolver` ContainerResolver plugin."""

import collections
import logging

import six

from ..container_resolvers import (
    ContainerResolver,
)
from ..docker_util import build_docker_images_command
from ..mulled.mulled_build import (
    check_output,
    DEFAULT_CHANNELS,
    ensure_installed,
    InvolucroContext,
    mull_targets,
)
from ..mulled.mulled_build_tool import requirements_to_mulled_targets
from ..mulled.util import (
    mulled_tags_for,
    split_tag,
    v1_image_name,
    v2_image_name,
)
from ..requirements import ContainerDescription

log = logging.getLogger(__name__)


CachedMulledImageSingleTarget = collections.namedtuple("CachedMulledImageSingleTarget", ["package_name", "version", "build", "image_identifier"])
CachedV1MulledImageMultiTarget = collections.namedtuple("CachedV1MulledImageMultiTarget", ["hash", "build", "image_identifier"])
CachedV2MulledImageMultiTarget = collections.namedtuple("CachedV2MulledImageMultiTarget", ["package_hash", "version_hash", "build", "image_identifier"])

CachedMulledImageSingleTarget.multi_target = False
CachedV1MulledImageMultiTarget.multi_target = "v1"
CachedV2MulledImageMultiTarget.multi_target = "v2"


def list_cached_mulled_images(namespace=None, hash_func="v2"):
    command = build_docker_images_command(truncate=True, sudo=False)
    command = "%s | tail -n +2 | tr -s ' ' | cut -d' ' -f1,2" % command
    images_and_versions = check_output(command)
    name_filter = get_filter(namespace)

    def output_line_to_image(line):
        image_name, version = line.split(" ", 1)
        identifier = "%s:%s" % (image_name, version)
        url, namespace, package_description = image_name.split("/")
        if not version or version == "latest":
            version = None

        image = None
        if package_description.startswith("mulled-v1-"):
            if hash_func == "v2":
                return None

            hash = package_description
            build = None
            if version and version.isdigit():
                build = version
            image = CachedV1MulledImageMultiTarget(hash, build, identifier)
        elif package_description.startswith("mulled-v2-"):
            if hash_func == "v1":
                return None

            version_hash = None
            build = None

            if version and "-" in version:
                version_hash, build = version.rsplit("-", 1)
            elif version.isdigit():
                version_hash, build = None, version
            elif version:
                log.debug("Unparsable mulled image tag encountered [%s]" % version)

            image = CachedV2MulledImageMultiTarget(package_description, version_hash, build, identifier)
        else:
            build = None
            if version and "--" in version:
                version, build = split_tag(version)

            image = CachedMulledImageSingleTarget(image_name, version, build, identifier)

        return image

    # TODO: Sort on build ...
    raw_images = [output_line_to_image(_) for _ in filter(name_filter, images_and_versions.splitlines())]
    return [i for i in raw_images if i is not None]


def get_filter(namespace):
    prefix = "quay.io/" if namespace is None else "quay.io/%s" % namespace
    return lambda name: name.startswith(prefix) and name.count("/") == 2


def cached_container_description(targets, namespace, hash_func="v2"):
    if len(targets) == 0:
        return None

    cached_images = list_cached_mulled_images(namespace, hash_func=hash_func)
    image = None
    if len(targets) == 1:
        target = targets[0]
        for cached_image in cached_images:
            if cached_image.multi_target:
                continue
            if not cached_image.package_name == target.package_name:
                continue
            if not target.version or target.version == cached_image.version:
                image = cached_image
                break
    elif hash_func == "v2":
        name = v2_image_name(targets)
        if ":" in name:
            package_hash, version_hash = name.split(":", 2)
        else:
            package_hash, version_hash = name, None

        for cached_image in cached_images:
            if cached_image.multi_target != "v2":
                continue

            if version_hash is None:
                # Just match on package hash...
                if package_hash == cached_image.package_hash:
                    image = cached_image
                    break
            else:
                # Match on package and version hash...
                if package_hash == cached_image.package_hash and version_hash == cached_image.version_hash:
                    image = cached_image
                    break

    elif hash_func == "v1":
        name = v1_image_name(targets)
        for cached_image in cached_images:
            if cached_image.multi_target != "v1":
                continue

            if name == cached_image.hash:
                image = cached_image
                break

    container = None
    if image:
        container = ContainerDescription(
            image.image_identifier,
            type="docker",
        )

    return container


@six.python_2_unicode_compatible
class CachedMulledContainerResolver(ContainerResolver):

    resolver_type = "cached_mulled"

    def __init__(self, app_info=None, namespace=None, hash_func="v2"):
        super(CachedMulledContainerResolver, self).__init__(app_info)
        self.namespace = namespace
        self.hash_func = hash_func

    def resolve(self, enabled_container_types, tool_info):
        if tool_info.requires_galaxy_python_environment:
            return None

        targets = mulled_targets(tool_info)
        return cached_container_description(targets, self.namespace, hash_func=self.hash_func)

    def __str__(self):
        return "CachedMulledContainerResolver[namespace=%s]" % self.namespace


@six.python_2_unicode_compatible
class MulledContainerResolver(ContainerResolver):
    """Look for mulled images matching tool dependencies."""

    resolver_type = "mulled"

    def __init__(self, app_info=None, namespace="biocontainers", hash_func="v2"):
        super(MulledContainerResolver, self).__init__(app_info)
        self.namespace = namespace
        self.hash_func = hash_func

    def resolve(self, enabled_container_types, tool_info):
        if tool_info.requires_galaxy_python_environment:
            return None

        targets = mulled_targets(tool_info)
        if len(targets) == 0:
            return None

        name = None

        if len(targets) == 1:
            target = targets[0]
            target_version = target.version
            tags = mulled_tags_for(self.namespace, target.package_name)

            if not tags:
                return None

            if target_version:
                for tag in tags:
                    version, build = split_tag(tag)
                    if version == target_version:
                        name = "%s:%s--%s" % (target.package_name, version, build)
                        break
            else:
                version, build = split_tag(tags[0])
                name = "%s:%s--%s" % (target.package_name, version, build)
        else:
            def tags_if_available(image_name):
                if ":" in image_name:
                    repo_name, tag_prefix = image_name.split(":", 2)
                else:
                    repo_name = image_name
                    tag_prefix = None
                tags = mulled_tags_for(self.namespace, repo_name, tag_prefix=tag_prefix)
                return tags

            if self.hash_func == "v2":
                base_image_name = v2_image_name(targets)
                tags = tags_if_available(base_image_name)
                if tags:
                    name = "%s:%s" % (base_image_name, tags[0])
            elif self.hash_func == "v1":
                base_image_name = v1_image_name(targets)
                tags = tags_if_available(base_image_name)
                if tags:
                    name = "%s:%s" % (base_image_name, tags[0])

        if name:
            return ContainerDescription(
                "quay.io/%s/%s" % (self.namespace, name),
                type="docker",
            )

    def __str__(self):
        return "MulledContainerResolver[namespace=%s]" % self.namespace


@six.python_2_unicode_compatible
class BuildMulledContainerResolver(ContainerResolver):
    """Look for mulled images matching tool dependencies."""

    resolver_type = "build_mulled"

    def __init__(self, app_info=None, namespace="local", hash_func="v2", **kwds):
        super(BuildMulledContainerResolver, self).__init__(app_info)
        self._involucro_context_kwds = {
            'involucro_bin': self._get_config_option("involucro_path", None)
        }
        self.namespace = namespace
        self.hash_func = hash_func
        self._mulled_kwds = {
            'namespace': namespace,
            'channels': self._get_config_option("channels", DEFAULT_CHANNELS, prefix="mulled"),
        }
        self.auto_init = self._get_config_option("auto_init", DEFAULT_CHANNELS, prefix="involucro")

    def resolve(self, enabled_container_types, tool_info):
        if tool_info.requires_galaxy_python_environment:
            return None

        targets = mulled_targets(tool_info)
        if len(targets) == 0:
            return None

        mull_targets(
            targets,
            involucro_context=self._get_involucro_context(),
            hash_func=self.hash_func,
            **self._mulled_kwds
        )
        return cached_container_description(targets, self.namespace, hash_func=self.hash_func)

    def _get_involucro_context(self):
        involucro_context = InvolucroContext(**self._involucro_context_kwds)
        self.enabled = ensure_installed(involucro_context, self.auto_init)
        return involucro_context

    def __str__(self):
        return "BuildContainerResolver[namespace=%s]" % self.namespace


def mulled_targets(tool_info):
    return requirements_to_mulled_targets(tool_info.requirements)


__all__ = (
    "CachedMulledContainerResolver",
    "MulledContainerResolver",
    "BuildMulledContainerResolver",
)
