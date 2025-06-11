"""The module defines the abstract interface for resolving container images for tool execution."""

import logging
import os
from abc import (
    ABCMeta,
    abstractmethod,
)
from typing import (
    Any,
    Container,
    List,
    NamedTuple,
    Optional,
    Type,
    TYPE_CHECKING,
    Union,
)

from typing_extensions import Literal

from galaxy.util import (
    safe_makedirs,
    string_as_bool,
    which,
)
from galaxy.util.bunch import Bunch
from galaxy.util.dictifiable import Dictifiable
from ..apptainer_util import (
    ApptainerContext,
    DEFAULT_APPTAINER_COMMAND,
    install_apptainer,
)

if TYPE_CHECKING:
    from beaker.cache import Cache

    from ..dependencies import (
        AppInfo,
        ToolInfo,
    )
    from ..requirements import ContainerDescription

log = logging.getLogger(__name__)


class CachedMulledImageSingleTarget(NamedTuple):
    package_name: str
    version: Optional[str]
    build: Optional[str]
    image_identifier: str


class CachedV1MulledImageMultiTarget(NamedTuple):
    hash: str
    build: Optional[str]
    image_identifier: str


class CachedV2MulledImageMultiTarget(NamedTuple):
    image_name: str
    version_hash: Optional[str]
    build: Optional[str]
    image_identifier: str

    @property
    def package_hash(self) -> str:
        # Make this work for Singularity file name or fully qualified Docker repository
        # image names.
        image_name = self.image_name
        if "/" not in image_name:
            return image_name
        else:
            return image_name.rsplit("/")[-1]


CachedTarget = Union[CachedMulledImageSingleTarget, CachedV1MulledImageMultiTarget, CachedV2MulledImageMultiTarget]


class ResolutionCache(Bunch):
    """Simple cache for duplicated computation created once per set of requests (likely web request in Galaxy context).

    This should not be assumed to be thread safe - resolution using a given cache should all occur
    one resolution at a time in a single thread.
    """

    mulled_resolution_cache: Optional["Cache"] = None


class CacheDirectory(metaclass=ABCMeta):
    def __init__(self, path: str, hash_func: Literal["v1", "v2"] = "v2") -> None:
        self.path = path
        self.hash_func = hash_func

    def _list_cached_images_from_path(self) -> List[CachedTarget]:
        contents = os.listdir(self.path)
        sorted_images = version_sorted(contents)
        raw_images = (identifier_to_cached_target(name, self.hash_func) for name in sorted_images)
        return [i for i in raw_images if i is not None]

    @abstractmethod
    def list_cached_images_from_path(self) -> List[CachedTarget]:
        """Generate a list of cached, mulled images in the cache."""

    @abstractmethod
    def invalidate_cache(self) -> None:
        """Invalidate the cache."""


class UncachedCacheDirectory(CacheDirectory):
    cacher_type = "uncached"

    def list_cached_images_from_path(
        self,
    ) -> List[CachedTarget]:
        return self._list_cached_images_from_path()

    def invalidate_cache(self) -> None:
        pass


class DirMtimeCacheDirectory(CacheDirectory):
    cacher_type = "dir_mtime"

    def __init__(self, path: str, **kwargs):
        super().__init__(path, **kwargs)
        self.invalidate_cache()

    def __get_mtime(self) -> float:
        return os.stat(self.path).st_mtime

    def __cache(self) -> None:
        self.__contents = self._list_cached_images_from_path()
        self.__mtime = self.__get_mtime()
        log.debug(f"Cached images in path {self.path} at directory mtime {self.__mtime}")

    def list_cached_images_from_path(
        self,
    ) -> List[CachedTarget]:
        mtime = self.__get_mtime()
        if mtime != self.__mtime:
            if mtime < self.__mtime:
                log.warning(
                    f"Modification time '{mtime}' of cache directory '{self.path}' is older than previous "
                    f"modification time '{self.__mtime}'! Cache directory will be recached"
                )
            self.__cache()
        return self.__contents

    def invalidate_cache(self) -> None:
        self.__mtime = -1.0
        self.__contents = []


class ContainerResolver(Dictifiable, metaclass=ABCMeta):
    """Description of a technique for resolving container images for tool execution."""

    # Keys for dictification.
    dict_collection_visible_keys = ["resolver_type", "can_uninstall_dependencies", "builds_on_resolution"]
    can_uninstall_dependencies = False
    builds_on_resolution = False
    read_only = True  # not used for containers, but set for when they are used like dependency resolvers

    def __init__(self, app_info: "AppInfo", **kwds) -> None:
        """Default initializer for ``ContainerResolver`` subclasses."""
        self.app_info = app_info
        self.resolver_kwds = kwds

    def _get_config_option(self, key: str, default: Any = None) -> Any:
        """Look in resolver-specific settings for option and then fallback to
        global settings.
        """
        return getattr(self.app_info, key, default)

    @abstractmethod
    def resolve(
        self, enabled_container_types: Container[str], tool_info: "ToolInfo", **kwds
    ) -> Optional["ContainerDescription"]:
        """Find a container matching all supplied requirements for tool.

        The supplied argument is a :class:`galaxy.tool_util.deps.dependencies.ToolInfo` description
        of the tool and its requirements.
        """

    @property
    @abstractmethod
    def resolver_type(self) -> str:
        """Short label for the type of container resolution."""

    def _container_type_enabled(
        self, container_description: "ContainerDescription", enabled_container_types: Container[str]
    ) -> bool:
        """Return a boolean indicating if the specified container type is enabled."""
        return container_description.type in enabled_container_types

    def __str__(self) -> str:
        return f"{self.__class__.__name__}[]"


class CliContainerResolver(ContainerResolver):
    container_type = "docker"
    cli = "docker"

    def __init__(self, app_info: "AppInfo", **kwargs) -> None:
        super().__init__(app_info=app_info, **kwargs)
        self._cli_available = bool(which(self.cli))

    @property
    def cli_available(self) -> bool:
        return self._cli_available

    @cli_available.setter
    def cli_available(self, value: bool) -> None:
        if not value:
            log.info(
                f"{self.cli} CLI not available, cannot list or pull images in Galaxy process. Does not impact kubernetes."
            )
        self._cli_available = value


class SingularityCliContainerResolver(CliContainerResolver):
    container_type = "singularity"
    cli = "singularity"
    cmd = None

    def __init__(self, app_info: "AppInfo", hash_func: Literal["v1", "v2"] = "v2", **kwargs) -> None:
        super().__init__(app_info=app_info, **kwargs)
        self.hash_func = hash_func
        self.cache_directory_cacher_type = kwargs.get("cache_directory_cacher_type")
        cacher_class = get_cache_directory_cacher(self.cache_directory_cacher_type)
        cache_directory_path = kwargs.get("cache_directory")
        if not cache_directory_path:
            assert self.app_info.container_image_cache_path
            cache_subdirectory = "mulled" if "mulled" in self.resolver_type else "explicit"
            cache_directory_path = os.path.join(
                self.app_info.container_image_cache_path, "singularity", cache_subdirectory
            )
        self.cache_directory = cacher_class(cache_directory_path, hash_func=self.hash_func)
        safe_makedirs(self.cache_directory.path)


class ApptainerCliContainerResolver(SingularityCliContainerResolver):
    container_type = "singularity"
    cli = "apptainer"
    cmd = None

    def __init__(self, app_info: "AppInfo", auto_init: bool = False, **kwargs) -> None:
        super().__init__(app_info=app_info, **kwargs)
        self.auto_init = string_as_bool(auto_init)
        apptainer_exec = kwargs.get("exec")
        if self.auto_init:
            apptainer_prefix = kwargs.get("prefix")
            if apptainer_prefix is None and apptainer_exec is None:
                assert self.app_info.apptainer_prefix
                apptainer_prefix = self.app_info.apptainer_prefix
            apptainer_context = ApptainerContext(apptainer_prefix=apptainer_prefix, apptainer_exec=apptainer_exec)
            deps_ensure_installed(apptainer_context, install_apptainer, self.auto_init)
            apptainer_exec = apptainer_context.apptainer_exec
            self._cli_available = True
        self.apptainer_exec = apptainer_exec
        self.cmd = apptainer_exec or DEFAULT_APPTAINER_COMMAND


def get_cache_directory_cacher(cacher_type: Optional[str]) -> Type[CacheDirectory]:
    # these can become a separate module and use plugin_config if we need more
    cachers: Dict[str, Type[CacheDirectory]] = {
        UncachedCacheDirectory.cacher_type: UncachedCacheDirectory,
        DirMtimeCacheDirectory.cacher_type: DirMtimeCacheDirectory,
    }
    cacher_type = cacher_type or "uncached"
    return cachers[cacher_type]
