"""Utilities for working with mulled abstractions outside the mulled package."""

import collections
import hashlib
import logging
import os
import re
import sys
import threading
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    TYPE_CHECKING,
    Union,
)

from conda_package_streaming.package_streaming import stream_conda_info
from conda_package_streaming.url import stream_conda_info as stream_conda_info_from_url
from packaging.version import Version
from requests import Session

from galaxy.tool_util.deps.conda_util import CondaTarget
from galaxy.tool_util.version import (
    LegacyVersion,
    parse_version,
)
from galaxy.util import requests

if TYPE_CHECKING:
    from galaxy.tool_util.deps.container_resolvers import ResolutionCache

log = logging.getLogger(__name__)

QUAY_REPOSITORY_API_ENDPOINT = "https://quay.io/api/v1/repository"
BUILD_NUMBER_REGEX = re.compile(r"\d+$")
MULLED_SOCKET_TIMEOUT = 12
QUAY_VERSIONS_CACHE_EXPIRY = 300
NAMESPACE_HAS_REPO_NAME_KEY = "galaxy.tool_util.deps.container_resolvers.mulled.util:namespace_repo_names"
TAG_CACHE_KEY = "galaxy.tool_util.deps.container_resolvers.mulled.util:tag_cache"


class PARSED_TAG(NamedTuple):
    tag: str
    version: Union[LegacyVersion, Version]
    build_string: Union[LegacyVersion, Version]
    build_number: int


def default_mulled_conda_channels_from_env() -> Optional[List[str]]:
    if "DEFAULT_MULLED_CONDA_CHANNELS" in os.environ:
        return os.environ["DEFAULT_MULLED_CONDA_CHANNELS"].split(",")
    else:
        return None


def create_repository(namespace: str, repo_name: str, oauth_token: str) -> None:
    assert oauth_token
    headers = {"Authorization": f"Bearer {oauth_token}"}
    data = {
        "repository": repo_name,
        "namespace": namespace,
        "description": "",
        "visibility": "public",
    }
    requests.post("https://quay.io/api/v1/repository", json=data, headers=headers, timeout=MULLED_SOCKET_TIMEOUT)


def quay_versions(namespace: str, pkg_name: str, session: Optional[Session] = None) -> List[str]:
    """Get all version tags for a Docker image stored on quay.io for supplied package name."""
    data = quay_repository(namespace, pkg_name, session=session)

    if "error_type" in data and data["error_type"] == "invalid_token":
        return []

    if "tags" not in data:
        raise Exception(f"Unexpected response from quay.io - no tags description found [{data}]")

    return [tag for tag in data["tags"].keys() if tag != "latest"]


def quay_repository(namespace: str, pkg_name: str, session: Optional[Session] = None) -> Dict[str, Any]:
    assert namespace is not None
    assert pkg_name is not None
    url = f"https://quay.io/api/v1/repository/{namespace}/{pkg_name}"
    if not session:
        session = requests.session()
    response = session.get(url, timeout=MULLED_SOCKET_TIMEOUT)
    data = response.json()
    return data


def _get_namespace(namespace: str) -> List[str]:
    log.debug(f"Querying {QUAY_REPOSITORY_API_ENDPOINT} for repos within {namespace}")
    next_page = None
    repo_names = []
    repos_headers = {"Accept-encoding": "gzip", "Accept": "application/json"}
    while True:
        repos_parameters = {"public": "true", "namespace": namespace, "next_page": next_page}
        repos_response = requests.get(
            QUAY_REPOSITORY_API_ENDPOINT, headers=repos_headers, params=repos_parameters, timeout=MULLED_SOCKET_TIMEOUT
        )
        repos_response_json = repos_response.json()
        repos = repos_response_json["repositories"]
        repo_names += [r["name"] for r in repos]
        next_page = repos_response_json.get("next_page")
        if not next_page:
            break
    return repo_names


def _namespace_has_repo_name(namespace: str, repo_name: str, resolution_cache: "ResolutionCache") -> bool:
    """
    Get all quay containers in the biocontainers repo
    """
    # resolution_cache.mulled_resolution_cache is the persistent variant of the resolution cache
    preferred_resolution_cache = resolution_cache.mulled_resolution_cache or resolution_cache
    cache_key = NAMESPACE_HAS_REPO_NAME_KEY
    if preferred_resolution_cache is not None:
        try:
            cached_namespace = preferred_resolution_cache.get(cache_key)
            if cached_namespace:
                return repo_name in cached_namespace
        except KeyError:
            # preferred_resolution_cache may be a beaker Cache instance, which
            # raises KeyError if key is not present on `.get`
            pass
    repo_names = _get_namespace(namespace)
    if preferred_resolution_cache is not None:
        preferred_resolution_cache[cache_key] = repo_names
    return repo_name in repo_names


def mulled_tags_for(
    namespace: str,
    image: str,
    tag_prefix: Optional[str] = None,
    resolution_cache: Optional["ResolutionCache"] = None,
    session: Optional[Session] = None,
    expire: float = QUAY_VERSIONS_CACHE_EXPIRY,
) -> List[str]:
    """Fetch remote tags available for supplied image name.

    The result will be sorted so newest tags are first.
    """
    if resolution_cache is not None:
        # Following check is pretty expensive against biocontainers... don't even bother doing it
        # if can't cache the response.
        if not _namespace_has_repo_name(namespace, image, resolution_cache):
            log.info(f"skipping mulled_tags_for [{image}] no repository")
            return []

    cache_key = TAG_CACHE_KEY
    if resolution_cache is not None:
        if resolution_cache.mulled_resolution_cache is not None:
            # Use persistent cache if possible. Since tags query is lightweight use a relatively short expiry time.
            resolution_cache = resolution_cache.mulled_resolution_cache._get_cache(
                "mulled_tag_cache", {"expire": expire}
            )
        assert resolution_cache is not None
        if cache_key not in resolution_cache:
            resolution_cache[cache_key] = collections.defaultdict(dict)
        tag_cache = resolution_cache.get(cache_key)
    else:
        tag_cache = collections.defaultdict(dict)

    tags_cached = False
    try:
        tags = tag_cache[namespace][image]
        tags_cached = True
    except KeyError:
        pass

    if not tags_cached:
        tags = quay_versions(namespace, image, session)
        tag_cache[namespace][image] = tags

    if tag_prefix is not None:
        tags = [t for t in tags if t.startswith(tag_prefix)]
    tags = version_sorted(tags)
    return tags


def split_tag(tag: str) -> List[str]:
    """Split mulled image tag into conda version and conda build."""
    return tag.rsplit("--", 1)


def parse_tag(tag: str) -> PARSED_TAG:
    """Decompose tag of mulled images into version, build string and build number."""
    version = tag.rsplit(":")[-1]
    build_string = "-1"
    build_number = -1
    match = BUILD_NUMBER_REGEX.search(version)
    if match:
        build_number = int(match.group(0))
    if "--" in version:
        version, build_string = version.rsplit("--", 1)
    elif "-" in version:
        # Should be mulled multi-container image tag
        version, build_string = version.rsplit("-", 1)
    else:
        # We don't have a build number, and the BUILD_NUMBER_REGEX above is only accurate for build strings,
        # so set build number to -1. Any matching image:version combination with a build number
        # will be considered newer.
        build_number = -1
    return PARSED_TAG(
        tag=tag,
        version=parse_version(version),
        build_string=parse_version(build_string),
        build_number=build_number,
    )


def version_sorted(elements: Iterable[str]) -> List[str]:
    """Sort iterable based on loose description of "version" from newest to oldest."""
    parsed_tags_iter = (parse_tag(tag) for tag in elements)
    sorted_tags = sorted(parsed_tags_iter, key=lambda tag: tag.build_string, reverse=True)
    sorted_tags = sorted(sorted_tags, key=lambda tag: tag.build_number, reverse=True)
    sorted_tags = sorted(sorted_tags, key=lambda tag: tag.version, reverse=True)
    return [e.tag for e in sorted_tags]


def build_target(
    package_name: str, version: Optional[str] = None, build: Optional[str] = None, tag: Optional[str] = None
) -> CondaTarget:
    """Use supplied arguments to build a :class:`CondaTarget` object."""
    if tag is not None:
        assert version is None
        assert build is None
        version, build = split_tag(tag)

    # conda package and quay image names are lowercase
    return CondaTarget(package_name, version=version, build=build)


def conda_build_target_str(target: CondaTarget) -> str:
    rval = target.package
    if target.version:
        rval += f"={target.version}"

        if target.build:
            rval += f"={target.build}"

    return rval


def _simple_image_name(targets: List[CondaTarget], image_build: Optional[str] = None) -> str:
    target = targets[0]
    suffix = ""
    if target.version is not None:
        build = target.build
        if build is None and image_build is not None and image_build != "0":
            # Special case image_build == "0", which has been built without a suffix
            print("WARNING: Hard-coding image build instead of using Conda build - this is not recommended.")
            build = image_build
        suffix += f":{target.version}"
        if build is not None:
            suffix += f"--{build}"
    return f"{target.package}{suffix}"


def v1_image_name(
    targets: Iterable[CondaTarget], image_build: Optional[str] = None, name_override: Optional[str] = None
) -> str:
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
        print(
            "WARNING: Overriding mulled image name, auto-detection of 'mulled' package attributes will fail to detect result."
        )
        return name_override

    targets = list(targets)
    if len(targets) == 1:
        return _simple_image_name(targets, image_build=image_build)
    else:
        targets_order = sorted(targets, key=lambda t: t.package)
        requirements_buffer = "\n".join(map(conda_build_target_str, targets_order))
        m = hashlib.sha1()
        m.update(requirements_buffer.encode())
        suffix = "" if not image_build else f":{image_build}"
        return f"mulled-v1-{m.hexdigest()}{suffix}"


def v2_image_name(
    targets: Iterable[CondaTarget], image_build: Optional[str] = None, name_override: Optional[str] = None
) -> str:
    """Generate mulled hash version 2 container identifier for supplied arguments.

    If a single target is specified, simply use the supplied name and version as
    the repository name and tag respectively. If multiple targets are supplied,
    hash the package names as the repository name and hash the package versions (if set)
    as the tag.

    >>> single_targets = [build_target("samtools", version="1.3.1")]
    >>> v2_image_name(single_targets)
    'samtools:1.3.1'
    >>> single_targets = [build_target("samtools", version="1.3.1", build="py_1")]
    >>> v2_image_name(single_targets)
    'samtools:1.3.1--py_1'
    >>> single_targets = [build_target("samtools", version="1.3.1")]
    >>> v2_image_name(single_targets, image_build="0")
    'samtools:1.3.1'
    >>> single_targets = [build_target("samtools", version="1.3.1", build="py_1")]
    >>> v2_image_name(single_targets, image_build="0")
    'samtools:1.3.1--py_1'
    >>> multi_targets = [build_target("samtools", version="1.3.1"), build_target("bwa", version="0.7.13")]
    >>> v2_image_name(multi_targets)
    'mulled-v2-fe8faa35dbf6dc65a0f7f5d4ea12e31a79f73e40:4d0535c94ef45be8459f429561f0894c3fe0ebcf'
    >>> multi_targets_on_versionless = [build_target("samtools", version="1.3.1"), build_target("bwa")]
    >>> v2_image_name(multi_targets_on_versionless)
    'mulled-v2-fe8faa35dbf6dc65a0f7f5d4ea12e31a79f73e40:b0c847e4fb89c343b04036e33b2daa19c4152cf5'
    >>> multi_targets_versionless = [build_target("samtools"), build_target("bwa")]
    >>> v2_image_name(multi_targets_versionless)
    'mulled-v2-fe8faa35dbf6dc65a0f7f5d4ea12e31a79f73e40'
    >>> targets_version_with_build = [build_target("samtools", version="1.3.1=h9071d68_10"), build_target("bedtools", version="2.26.0=0")]
    >>> v2_image_name(targets_version_with_build)
    'mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:8e86df67d257ce6494ae12b2c60e1b94025ea529'
    >>> targets_version_with_build = [build_target("samtools", version="1.3.1", build="h9071d68_10"), build_target("bedtools", version="2.26.0", build="0")]
    >>> v2_image_name(targets_version_with_build)
    'mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619'
    """

    if name_override is not None:
        print(
            "WARNING: Overriding mulled image name, auto-detection of 'mulled' package attributes will fail to detect result."
        )
        return name_override

    targets = list(targets)
    if len(targets) == 1:
        return _simple_image_name(targets, image_build=image_build)
    else:
        targets_order = sorted(targets, key=lambda t: t.package)
        package_name_buffer = "\n".join(t.package for t in targets_order)
        package_hash = hashlib.sha1()
        package_hash.update(package_name_buffer.encode())

        versions = (t.version for t in targets_order)
        if any(versions):
            # Only hash versions if at least one package has versions...
            version_name_buffer = "\n".join(t.version or "null" for t in targets_order)
            version_hash = hashlib.sha1()
            version_hash.update(version_name_buffer.encode())
            version_hash_str = version_hash.hexdigest()
        else:
            version_hash_str = ""

        if not image_build:
            build_suffix = ""
        elif version_hash_str:
            # tagged verson is <version_hash>-<build>
            build_suffix = f"-{image_build}"
        else:
            # tagged version is simply the build
            build_suffix = image_build
        suffix = ""
        if version_hash_str or build_suffix:
            suffix = f":{version_hash_str}{build_suffix}"
        return f"mulled-v2-{package_hash.hexdigest()}{suffix}"


def get_files_from_conda_package(url: str, filepaths: Iterable[str]) -> Dict[str, bytes]:
    """
    Get content of specified files in a conda package.
    The url can be a path to a local file or an url.
    The filepaths is an iterable of paths to extract from the conda package, if
    found in it.
    Return a dictionary mapping each found filepath to the corresponding content
    (as bytes).

    >>> content_dict = get_files_from_conda_package("https://anaconda.org/conda-forge/chopin2/1.0.6/download/noarch/chopin2-1.0.6-pyhd8ed1ab_0.tar.bz2", ["info/recipe/meta.yaml"])
    >>> assert "info/recipe/meta.yaml" in content_dict, content_dict
    >>> assert isinstance(content_dict["info/recipe/meta.yaml"], bytes)
    >>> content_dict = get_files_from_conda_package("https://anaconda.org/conda-forge/chopin2/1.0.7/download/noarch/chopin2-1.0.7-pyhd8ed1ab_1.conda", ["info/about.json", "info/recipe/meta.yaml", "foo/bar"])
    >>> assert sorted(content_dict.keys()) == ["info/about.json", "info/recipe/meta.yaml"], content_dict
    """

    try:
        stream = stream_conda_info(url)
    except FileNotFoundError:
        stream = stream_conda_info_from_url(url)
    ret = {}
    for tar, member in stream:
        if member.name in filepaths:
            ret[member.name] = tar.extractfile(member).read()
    return ret


def split_container_name(name: str) -> List[str]:
    """
    Takes a container name (e.g. samtools:1.7--1) and returns a list (e.g. ['samtools', '1.7', '1'])
    >>> split_container_name('samtools:1.7--1')
    ['samtools', '1.7', '1']
    """
    return name.replace("--", ":").split(":")


class PrintProgress:
    def __init__(self) -> None:
        self.thread = threading.Thread(target=self.progress)
        self.stop = threading.Event()

    def progress(self) -> None:
        while not self.stop.is_set():
            print(".", end="")
            sys.stdout.flush()
            self.stop.wait(60)
        print("")

    def __enter__(self) -> "PrintProgress":
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop.set()
        self.thread.join()


image_name = v1_image_name  # deprecated

__all__ = (
    "build_target",
    "conda_build_target_str",
    "get_files_from_conda_package",
    "image_name",
    "mulled_tags_for",
    "quay_versions",
    "split_container_name",
    "split_tag",
    "v1_image_name",
    "v2_image_name",
    "version_sorted",
)
