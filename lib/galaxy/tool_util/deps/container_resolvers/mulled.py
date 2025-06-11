"""This module describes the :class:`MulledContainerResolver` ContainerResolver plugin."""

import logging
import os
import subprocess
from typing import (
    Any,
    Container as TypingContainer,
    Dict,
    List,
    Optional,
    TYPE_CHECKING,
)

from requests import Session
from typing_extensions import Literal

from galaxy.util import (
    string_as_bool,
)
from galaxy.util.commands import shell
from . import (
    ApptainerCliContainerResolver,
    CacheDirectory,
    CachedMulledImageSingleTarget,
    CachedTarget,
    CachedV1MulledImageMultiTarget,
    CachedV2MulledImageMultiTarget,
    CliContainerResolver,
    ResolutionCache,
    SingularityCliContainerResolver,
    list_docker_cached_mulled_images,
)
from ..conda_util import CondaTarget
from ..container_classes import (
    Container,
    CONTAINER_CLASSES,
    DockerContainer,
    SingularityContainer,
)
from ..mulled.mulled_build import (
    ensure_installed,
    InvolucroContext,
    mull_targets,
)
from ..mulled.mulled_build_tool import requirements_to_mulled_targets
from ..mulled.util import (
    DEFAULT_CHANNELS,
    default_mulled_conda_channels_from_env,
    mulled_tags_for,
    split_tag,
    v1_image_name,
    v2_image_name,
)
from ..requirements import (
    ContainerDescription,
    DEFAULT_CONTAINER_SHELL,
)

if TYPE_CHECKING:
    from ..dependencies import (
        AppInfo,
        ToolInfo,
    )

log = logging.getLogger(__name__)


def find_best_matching_cached_image(
    targets: List[CondaTarget], cached_images: List[CachedTarget], hash_func: Literal["v1", "v2"]
) -> Optional[CachedTarget]:
    if len(targets) == 0:
        return None

    image: Optional[CachedTarget] = None
    cached_image: CachedTarget
    if len(targets) == 1:
        target = targets[0]
        for cached_image in cached_images:
            if not isinstance(cached_image, CachedMulledImageSingleTarget):
                continue
            if not cached_image.package_name == target.package:
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
            if not isinstance(cached_image, CachedV2MulledImageMultiTarget):
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
            if not isinstance(cached_image, CachedV1MulledImageMultiTarget):
                continue

            if name == cached_image.hash:
                image = cached_image
                break
    return image


def docker_cached_container_description(
    targets: List[CondaTarget],
    namespace: str,
    hash_func: Literal["v1", "v2"] = "v2",
    shell: str = DEFAULT_CONTAINER_SHELL,
    resolution_cache: Optional[ResolutionCache] = None,
) -> Optional[ContainerDescription]:
    if len(targets) == 0:
        return None

    cached_images = list_docker_cached_mulled_images(namespace, hash_func=hash_func, resolution_cache=resolution_cache)
    image = find_best_matching_cached_image(targets, cached_images, hash_func)

    container = None
    if image:
        container = ContainerDescription(
            image.image_identifier,
            type="docker",
            shell=shell,
        )

    return container


def singularity_cached_container_description(
    targets: List[CondaTarget],
    cache_directory: CacheDirectory,
    hash_func: Literal["v1", "v2"] = "v2",
    shell: str = DEFAULT_CONTAINER_SHELL,
    cmd: Optional[str] = None,
) -> Optional[ContainerDescription]:
    if len(targets) == 0:
        return None

    if not os.path.exists(cache_directory.path):
        return None

    cached_images = cache_directory.list_cached_images_from_path()
    image = find_best_matching_cached_image(targets, cached_images, hash_func)

    container = None
    if image:
        container = ContainerDescription(
            os.path.abspath(os.path.join(cache_directory.path, image.image_identifier)),
            type="singularity",
            shell=shell,
            cmd=cmd,
        )
    return container


def targets_to_mulled_name(
    targets: List[CondaTarget],
    hash_func: Literal["v1", "v2"],
    namespace: str,
    resolution_cache: Optional[ResolutionCache] = None,
    session: Optional[Session] = None,
) -> Optional[str]:
    unresolved_cache_key = "galaxy.tool_util.deps.container_resolvers.mulled:unresolved"
    if resolution_cache is not None:
        if unresolved_cache_key not in resolution_cache:
            resolution_cache[unresolved_cache_key] = set()
        unresolved_cache = resolution_cache.get(unresolved_cache_key)
    else:
        unresolved_cache = set()

    mulled_resolution_cache = None
    if resolution_cache and resolution_cache.mulled_resolution_cache:
        mulled_resolution_cache = resolution_cache.mulled_resolution_cache

    name = None

    def cached_name(cache_key: str) -> Optional[str]:
        if mulled_resolution_cache:
            try:
                return resolution_cache.get(cache_key)  # type: ignore[union-attr] # mulled_resolution_cache not None implies resolution_cache not None
            except KeyError:
                return None
        return None

    if len(targets) == 1:
        target = targets[0]
        target_version = target.version
        cache_key = f"ns[{namespace}]__single__{target.package}__@__{target_version}"
        if cache_key in unresolved_cache:
            return None
        name = cached_name(cache_key)
        if name:
            return name

        tags = mulled_tags_for(namespace, target.package, resolution_cache=resolution_cache, session=session)

        if tags:
            for tag in tags:
                if "--" in tag:
                    version, _ = split_tag(tag)
                else:
                    version = tag
                if target_version and version == target_version:
                    name = f"{target.package}:{tag}"
                    break

    else:

        def first_tag_if_available(image_name):
            if ":" in image_name:
                repo_name, tag_prefix = image_name.split(":", 2)
            else:
                repo_name = image_name
                tag_prefix = None
            tags = mulled_tags_for(
                namespace, repo_name, tag_prefix=tag_prefix, resolution_cache=resolution_cache, session=session
            )
            return tags[0] if tags else None

        if hash_func == "v2":
            base_image_name = v2_image_name(targets)
        elif hash_func == "v1":
            base_image_name = v1_image_name(targets)
        else:
            raise Exception(f"Unimplemented mulled hash_func [{hash_func}]")

        cache_key = f"ns[{namespace}]__{hash_func}__{base_image_name}"
        if cache_key in unresolved_cache:
            return None
        name = cached_name(cache_key)
        if name:
            return name

        tag = first_tag_if_available(base_image_name)
        if tag:
            if ":" in base_image_name:
                assert hash_func != "v1"
                # base_image_name of form <package_hash>:<version_hash>, expand tag
                # to include build number in tag.
                name = f"{base_image_name.split(':')[0]}:{tag}"
            else:
                # base_image_name of form <package_hash>, simply add build number
                # as tag to fully qualify image.
                name = f"{base_image_name}:{tag}"

    if name and mulled_resolution_cache:
        mulled_resolution_cache.put(cache_key, name)

    if name is None:
        unresolved_cache.add(name)

    return name


class CachedMulledDockerContainerResolver(CliContainerResolver):
    resolver_type = "cached_mulled"
    shell = "/bin/bash"

    def __init__(
        self, app_info: "AppInfo", namespace: str = "biocontainers", hash_func: Literal["v1", "v2"] = "v2", **kwds
    ):
        super().__init__(app_info=app_info, **kwds)
        self.namespace = namespace
        self.hash_func = hash_func

    def resolve(
        self, enabled_container_types: TypingContainer[str], tool_info: "ToolInfo", **kwds
    ) -> Optional[ContainerDescription]:
        if (
            not self.cli_available
            or tool_info.requires_galaxy_python_environment
            or self.container_type not in enabled_container_types
        ):
            return None

        targets = mulled_targets(tool_info)
        log.debug(f"Image name for tool {tool_info.tool_id}: {image_name(targets, self.hash_func)}")
        resolution_cache = kwds.get("resolution_cache")
        return docker_cached_container_description(
            targets, self.namespace, hash_func=self.hash_func, shell=self.shell, resolution_cache=resolution_cache
        )

    def __str__(self):
        return f"CachedMulledDockerContainerResolver[namespace={self.namespace}]"


class CachedMulledSingularityContainerResolver(SingularityCliContainerResolver):
    resolver_type = "cached_mulled_singularity"
    shell = "/bin/bash"

    def resolve(
        self, enabled_container_types: TypingContainer[str], tool_info: "ToolInfo", **kwds
    ) -> Optional[ContainerDescription]:
        if tool_info.requires_galaxy_python_environment or self.container_type not in enabled_container_types:
            return None

        targets = mulled_targets(tool_info)
        log.debug(f"Image name for tool {tool_info.tool_id}: {image_name(targets, self.hash_func)}")
        return singularity_cached_container_description(
            targets,
            self.cache_directory,
            hash_func=self.hash_func,
            shell=self.shell,
            cmd=self.cmd,
        )

    def __str__(self) -> str:
        return f"CachedMulledSingularityContainerResolver[cache_directory={self.cache_directory.path}]"


class CachedMulledApptainerContainerResolver(ApptainerCliContainerResolver, CachedMulledSingularityContainerResolver):
    resolver_type = "cached_mulled_apptainer"
    shell = "/bin/bash"

    def __str__(self) -> str:
        return f"CachedMulledApptainerContainerResolver[cache_directory={self.cache_directory.path},apptainer_exec={self.apptainer_exec}]"


class MulledDockerContainerResolver(CliContainerResolver):
    """Look for mulled images matching tool dependencies."""

    resolver_type = "mulled"
    shell = "/bin/bash"
    protocol: Optional[str] = None

    def __init__(
        self,
        app_info: "AppInfo",
        namespace: str = "biocontainers",
        hash_func: Literal["v1", "v2"] = "v2",
        auto_install: bool = True,
        **kwds,
    ) -> None:
        super().__init__(app_info=app_info, **kwds)
        self.namespace = namespace
        self.hash_func = hash_func
        self.auto_install = string_as_bool(auto_install)

    def cached_container_description(
        self,
        targets: List[CondaTarget],
        namespace: str,
        hash_func: Literal["v1", "v2"],
        resolution_cache: Optional[ResolutionCache] = None,
    ) -> Optional[ContainerDescription]:
        try:
            return docker_cached_container_description(
                targets, namespace, hash_func=hash_func, resolution_cache=resolution_cache
            )
        except subprocess.CalledProcessError:
            # We should only get here if a docker binary is available, but command quits with a non-zero exit code,
            # e.g if the docker daemon is not available
            log.exception("An error occured while listing cached docker image. Docker daemon may need to be restarted.")
            return None

    def pull(self, container: Container) -> None:
        if self.cli_available:
            assert isinstance(container, DockerContainer)
            command = container.build_pull_command()
            shell(command)

    @property
    def can_list_containers(self) -> bool:
        return self.cli_available

    def resolve(
        self,
        enabled_container_types: TypingContainer[str],
        tool_info: "ToolInfo",
        install: bool = False,
        session: Optional[Session] = None,
        **kwds,
    ) -> Optional[ContainerDescription]:
        resolution_cache = kwds.get("resolution_cache")
        if tool_info.requires_galaxy_python_environment or self.container_type not in enabled_container_types:
            return None

        targets = mulled_targets(tool_info)
        log.debug(f"Image name for tool {tool_info.tool_id}: {image_name(targets, self.hash_func)}")
        if len(targets) == 0:
            return None

        name = targets_to_mulled_name(
            targets=targets,
            hash_func=self.hash_func,
            namespace=self.namespace,
            resolution_cache=resolution_cache,
            session=session,
        )
        if not name:
            return None
        container_id = f"quay.io/{self.namespace}/{name}"
        if self.protocol:
            container_id = f"{self.protocol}{container_id}"
        container_description = ContainerDescription(
            container_id,
            type=self.container_type,
            shell=self.shell,
        )
        if self.can_list_containers:
            if install and not self.cached_container_description(
                targets,
                namespace=self.namespace,
                hash_func=self.hash_func,
                resolution_cache=resolution_cache,
            ):
                destination_info = {}
                destination_for_container_type = kwds.get("destination_for_container_type")
                if destination_for_container_type:
                    destination_info = destination_for_container_type(self.container_type)
                container = CONTAINER_CLASSES[self.container_type](
                    container_description.identifier,
                    self.app_info,
                    tool_info,
                    destination_info,
                    None,
                    container_description,
                )
                self.pull(container)
            if not self.auto_install:
                container_description = (
                    self.cached_container_description(
                        targets,
                        namespace=self.namespace,
                        hash_func=self.hash_func,
                        resolution_cache=resolution_cache,
                    )
                    or container_description
                )
        return container_description

    def __str__(self) -> str:
        return f"MulledDockerContainerResolver[namespace={self.namespace}]"


class MulledSingularityContainerResolver(SingularityCliContainerResolver, MulledDockerContainerResolver):
    resolver_type = "mulled_singularity"
    protocol = "docker://"

    def __init__(
        self,
        app_info: "AppInfo",
        hash_func: Literal["v1", "v2"] = "v2",
        namespace: str = "biocontainers",
        auto_install: bool = True,
        **kwds,
    ) -> None:
        super().__init__(app_info=app_info, hash_func=hash_func, **kwds)
        self.namespace = namespace
        self.auto_install = string_as_bool(auto_install)

    def cached_container_description(
        self,
        targets: List[CondaTarget],
        namespace: str,
        hash_func: Literal["v1", "v2"],
        resolution_cache: Optional[ResolutionCache] = None,
    ) -> Optional[ContainerDescription]:
        return singularity_cached_container_description(
            targets, cache_directory=self.cache_directory, hash_func=hash_func
        )

    @property
    def can_list_containers(self) -> bool:
        # Only needs access to path, doesn't require CLI
        return True

    def pull(self, container: Container) -> None:
        if self.cli_available:
            assert isinstance(container, SingularityContainer)
            cmds = container.build_mulled_singularity_pull_command(
                cache_directory=self.cache_directory.path, namespace=self.namespace
            )
            shell(cmds=cmds)
            self.cache_directory.invalidate_cache()

    def __str__(self) -> str:
        return f"MulledSingularityContainerResolver[namespace={self.namespace}]"


class MulledApptainerContainerResolver(ApptainerCliContainerResolver, MulledSingularityContainerResolver):
    resolver_type = "mulled_apptainer"
    protocol = "docker://"

    def __str__(self) -> str:
        return f"MulledApptainerContainerResolver[namespace={self.namespace},apptainer_exec={self.apptainer_exec}]"


class BuildMulledDockerContainerResolver(CliContainerResolver):
    """Build for Docker mulled images matching tool dependencies."""

    resolver_type = "build_mulled"
    shell = "/bin/bash"
    builds_on_resolution = True

    def __init__(
        self,
        app_info: "AppInfo",
        namespace: str = "local",
        hash_func: Literal["v1", "v2"] = "v2",
        auto_install: bool = True,
        **kwds,
    ) -> None:
        super().__init__(app_info=app_info, **kwds)
        self._involucro_context_kwds = {"involucro_bin": self._get_config_option("involucro_path", None)}
        self.namespace = namespace
        self.hash_func = hash_func
        self.auto_install = string_as_bool(auto_install)
        self._mulled_kwds: Dict[str, Any] = {
            "namespace": namespace,
            "hash_func": self.hash_func,
            "command": "build-and-test",
            "use_mamba": False,
        }
        self._mulled_kwds["channels"] = default_mulled_conda_channels_from_env() or self._get_config_option(
            "mulled_channels", DEFAULT_CHANNELS
        )
        self.involucro_context = InvolucroContext(**self._involucro_context_kwds)
        auto_init = self._get_config_option("involucro_auto_init", True)
        self.enabled = ensure_installed(self.involucro_context, auto_init)

    def resolve(
        self, enabled_container_types: TypingContainer[str], tool_info: "ToolInfo", install: bool = False, **kwds
    ) -> Optional[ContainerDescription]:
        if tool_info.requires_galaxy_python_environment or self.container_type not in enabled_container_types:
            return None

        targets = mulled_targets(tool_info)
        log.debug(f"Image name for tool {tool_info.tool_id}: {image_name(targets, self.hash_func)}")
        if len(targets) == 0:
            return None
        if self.auto_install or install:
            mull_targets(targets, involucro_context=self.involucro_context, **self._mulled_kwds)
        return docker_cached_container_description(targets, self.namespace, hash_func=self.hash_func, shell=self.shell)

    def __str__(self) -> str:
        return f"BuildDockerContainerResolver[namespace={self.namespace}]"


class BuildMulledSingularityContainerResolver(SingularityCliContainerResolver):
    """Build for Singularity mulled images matching tool dependencies."""

    resolver_type = "build_mulled_singularity"
    shell = "/bin/bash"
    builds_on_resolution = True

    def __init__(
        self,
        app_info: "AppInfo",
        hash_func: Literal["v1", "v2"] = "v2",
        auto_install: bool = True,
        **kwds,
    ) -> None:
        super().__init__(app_info=app_info, hash_func=hash_func, **kwds)
        self._involucro_context_kwds = {"involucro_bin": self._get_config_option("involucro_path", None)}
        self.auto_install = string_as_bool(auto_install)
        self._mulled_kwds = {
            "channels": self._get_config_option("mulled_channels", DEFAULT_CHANNELS),
            "hash_func": self.hash_func,
            "command": "build-and-test",
            "namespace": "local",
            "singularity": True,
            "singularity_image_dir": self.cache_directory.path,
            "use_mamba": False,
        }
        self.involucro_context = InvolucroContext(**self._involucro_context_kwds)
        auto_init = self._get_config_option("involucro_auto_init", True)
        self.enabled = ensure_installed(self.involucro_context, auto_init)

    def resolve(
        self, enabled_container_types: TypingContainer[str], tool_info: "ToolInfo", install: bool = False, **kwds
    ) -> Optional[ContainerDescription]:
        if tool_info.requires_galaxy_python_environment or self.container_type not in enabled_container_types:
            return None

        targets = mulled_targets(tool_info)
        log.debug(f"Image name for tool {tool_info.tool_id}: {image_name(targets, self.hash_func)}")
        if len(targets) == 0:
            return None

        if self.auto_install or install:
            mull_targets(targets, involucro_context=self.involucro_context, **self._mulled_kwds)
        return singularity_cached_container_description(
            targets, self.cache_directory, hash_func=self.hash_func, shell=self.shell
        )

    def __str__(self) -> str:
        return f"BuildSingularityContainerResolver[cache_directory={self.cache_directory.path}]"


class BuildMulledApptainerContainerResolver(ApptainerCliContainerResolver, BuildMulledSingularityContainerResolver):
    resolver_type = "build_mulled_apptainer"
    shell = "/bin/bash"
    builds_on_resolution = True

    def __str__(self) -> str:
        return f"BuildApptainerContainerResolver[cache_directory={self.cache_directory.path},apptainer_exec={self.apptainer_exec}]"


def mulled_targets(tool_info: "ToolInfo") -> List[CondaTarget]:
    return requirements_to_mulled_targets(tool_info.requirements)


def image_name(targets: List[CondaTarget], hash_func: Literal["v1", "v2"]) -> str:
    if len(targets) == 0:
        return "no targets"
    elif hash_func == "v2":
        return v2_image_name(targets)
    else:
        return v1_image_name(targets)


__all__ = (
    "CachedMulledDockerContainerResolver",
    "CachedMulledSingularityContainerResolver",
    "CachedMulledApptainerContainerResolver",
    "MulledDockerContainerResolver",
    "MulledSingularityContainerResolver",
    "MulledApptainerContainerResolver",
    "BuildMulledDockerContainerResolver",
    "BuildMulledSingularityContainerResolver",
    "BuildMulledApptainerContainerResolver",
)
