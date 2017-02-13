"""This module describes the :class:`MulledContainerResolver` ContainerResolver plugin."""

import collections
import logging

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
    image_name,
    mulled_tags_for,
    split_tag,
)
from ..requirements import ContainerDescription

log = logging.getLogger(__name__)


CachedMulledImageSingleTarget = collections.namedtuple("CachedMulledImageSingleTarget", ["package_name", "version", "build", "image_identifier"])
CachedMulledImageMultiTarget = collections.namedtuple("CachedMulledImageMultiTarget", ["hash", "image_identifier"])

CachedMulledImageSingleTarget.multi_target = False
CachedMulledImageMultiTarget.multi_target = True


def list_cached_mulled_images(namespace=None):
    command = build_docker_images_command(truncate=True, sudo=False)
    command = "%s | tail -n +2 | tr -s ' ' | cut -d' ' -f1,2" % command
    images_and_versions = check_output(command)
    name_filter = get_filter(namespace)

    def output_line_to_image(line):
        image_name, version = line.split(" ", 1)
        identifier = "%s:%s" % (image_name, version)
        url, namespace, package_description = image_name.split("/")

        if package_description.startswith("mulled-v1-"):
            hash = package_description
            image = CachedMulledImageMultiTarget(hash, identifier)
        else:
            build = None
            if not version or version == "latest":
                version = None

            if version and "--" in version:
                version, build = split_tag(version)

            image = CachedMulledImageSingleTarget(image_name, version, build, identifier)

        return image

    return [output_line_to_image(_) for _ in filter(name_filter, images_and_versions.splitlines())]


def get_filter(namespace):
    prefix = "quay.io/" if namespace is None else "quay.io/%s" % namespace
    return lambda name: name.startswith(prefix) and name.count("/") == 2


def cached_container_description(targets, namespace):
    if len(targets) == 0:
        return None

    cached_images = list_cached_mulled_images(namespace)
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
    else:
        name = image_name(targets)
        for cached_image in cached_images:
            if not cached_image.multi_target:
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


class CachedMulledContainerResolver(ContainerResolver):

    resolver_type = "cached_mulled"

    def __init__(self, app_info=None, namespace=None):
        super(CachedMulledContainerResolver, self).__init__(app_info)
        self.namespace = namespace

    def resolve(self, enabled_container_types, tool_info):
        targets = mulled_targets(tool_info)
        return cached_container_description(targets, self.namespace)


class MulledContainerResolver(ContainerResolver):
    """Look for mulled images matching tool dependencies."""

    resolver_type = "mulled"

    def __init__(self, app_info=None, namespace="biocontainers"):
        super(MulledContainerResolver, self).__init__(app_info)
        self.namespace = namespace

    def resolve(self, enabled_container_types, tool_info):
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
            base_image_name = image_name(targets)
            tags = mulled_tags_for(self.namespace, base_image_name)
            if tags:
                name = "%s:%s" % (base_image_name, tags[0])

        if name:
            return ContainerDescription(
                "quay.io/%s/%s" % (self.namespace, name),
                type="docker",
            )


class BuildMulledContainerResolver(ContainerResolver):
    """Look for mulled images matching tool dependencies."""

    resolver_type = "build_mulled"

    def __init__(self, app_info=None, namespace="local", **kwds):
        super(BuildMulledContainerResolver, self).__init__(app_info)
        self._involucro_context_kwds = {
            'involucro_bin': self._get_config_option("involucro_path", None)
        }
        self.namespace = namespace
        self._mulled_kwds = {
            'namespace': namespace,
            'channels': self._get_config_option("channels", DEFAULT_CHANNELS, prefix="mulled"),
        }
        self.auto_init = self._get_config_option("auto_init", DEFAULT_CHANNELS, prefix="involucro")

    def resolve(self, enabled_container_types, tool_info):
        targets = mulled_targets(tool_info)
        if len(targets) == 0:
            return None

        mull_targets(
            targets,
            involucro_context=self._get_involucro_context(),
            **self._mulled_kwds
        )
        return cached_container_description(targets, self.namespace)

    def _get_involucro_context(self):
        involucro_context = InvolucroContext(**self._involucro_context_kwds)
        self.enabled = ensure_installed(involucro_context, self.auto_init)
        return involucro_context


def mulled_targets(tool_info):
    return requirements_to_mulled_targets(tool_info.requirements)


__all__ = (
    "CachedMulledContainerResolver",
    "MulledContainerResolver",
    "BuildMulledContainerResolver",
)
