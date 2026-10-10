"""Query OCI registries for the architectures an image is published for."""

import logging
import re
import threading

import requests

from .oci_arch import platform_to_oci_arch

log = logging.getLogger(__name__)

REGISTRY_TIMEOUT = 10
MANIFEST_ACCEPT = ", ".join(
    (
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
    )
)
_INDEX_TYPES = (
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.index.v1+json",
)
DOCKER_HUB_HOSTS = ("docker.io", "index.docker.io", "registry-1.docker.io")

_cache: dict[str, list[str]] = {}
_cache_lock = threading.Lock()


def parse_image_reference(image_ref: str) -> tuple[str, str, str]:
    """Split an image reference into registry host, repository and tag or digest.

    >>> parse_image_reference("docker://python:3.12-alpine")
    ('registry-1.docker.io', 'library/python', '3.12-alpine')
    >>> parse_image_reference("quay.io/biocontainers/samtools:1.20--h50ea8bc_0")
    ('quay.io', 'biocontainers/samtools', '1.20--h50ea8bc_0')
    >>> parse_image_reference("docker.io/user/tool")
    ('registry-1.docker.io', 'user/tool', 'latest')
    """
    ref = image_ref.strip()
    if "://" in ref:
        scheme, ref = ref.split("://", 1)
        if scheme != "docker":
            raise ValueError(f"unsupported image reference scheme '{scheme}'")
    reference = "latest"
    if "@" in ref:
        ref, reference = ref.split("@", 1)
    first, _, rest = ref.partition("/")
    if rest and ("." in first or ":" in first or first == "localhost"):
        host, repository = first, rest
    else:
        host, repository = "docker.io", ref
    if reference == "latest" and ":" in repository.rsplit("/", 1)[-1]:
        repository, reference = repository.rsplit(":", 1)
    if host in DOCKER_HUB_HOSTS:
        host = "registry-1.docker.io"
        if "/" not in repository:
            repository = f"library/{repository}"
    return host, repository, reference


def _bearer_token(challenge: str, repository: str) -> str | None:
    params = dict(re.findall(r'(\w+)="([^"]*)"', challenge))
    realm = params.get("realm")
    if not realm:
        return None
    query = {"scope": params.get("scope") or f"repository:{repository}:pull"}
    if params.get("service"):
        query["service"] = params["service"]
    response = requests.get(realm, params=query, timeout=REGISTRY_TIMEOUT)
    response.raise_for_status()
    body = response.json()
    return body.get("token") or body.get("access_token")


def _get(url: str, headers: dict[str, str], repository: str, state: dict[str, str]) -> "requests.Response":
    if state.get("token"):
        headers = dict(headers, Authorization=f"Bearer {state['token']}")
    response = requests.get(url, headers=headers, timeout=REGISTRY_TIMEOUT)
    if response.status_code == 401 and not state.get("token"):
        challenge = response.headers.get("Www-Authenticate", "")
        if challenge.lower().startswith("bearer"):
            token = _bearer_token(challenge, repository)
            if token:
                state["token"] = token
                return _get(url, headers, repository, state)
    response.raise_for_status()
    return response


def _query_architectures(image_ref: str) -> list[str]:
    host, repository, reference = parse_image_reference(image_ref)
    base = f"https://{host}/v2/{repository}"
    state: dict[str, str] = {}
    manifest_response = _get(f"{base}/manifests/{reference}", {"Accept": MANIFEST_ACCEPT}, repository, state)
    manifest = manifest_response.json()
    media_type = manifest.get("mediaType") or manifest_response.headers.get("Content-Type", "").split(";")[0]
    if media_type in _INDEX_TYPES or "manifests" in manifest:
        architectures = []
        for entry in manifest.get("manifests", []):
            arch = (entry.get("platform") or {}).get("architecture")
            if arch and arch != "unknown" and arch not in architectures:
                architectures.append(arch)
        return architectures
    config_digest = (manifest.get("config") or {}).get("digest")
    if not config_digest:
        raise ValueError("manifest without config digest")
    config = _get(f"{base}/blobs/{config_digest}", {}, repository, state).json()
    arch = config.get("architecture")
    if not arch:
        raise ValueError("image config without architecture")
    return [arch]


def registry_image_architectures(image_ref: str) -> list[str] | None:
    """Architectures ``image_ref`` is published for, or ``None`` if the registry could not tell.

    Results are cached per reference for the lifetime of the process. Any error yields ``None``.
    """
    with _cache_lock:
        if image_ref in _cache:
            return list(_cache[image_ref])
    try:
        architectures = _query_architectures(image_ref)
    except Exception as e:
        log.debug("Could not read the manifest of '%s' from its registry: %s", image_ref, e)
        return None
    if not architectures:
        return None
    with _cache_lock:
        _cache[image_ref] = architectures
    return list(architectures)


def missing_architecture(image_ref: str, platform: str | None) -> list[str] | None:
    """Architectures that exist for ``image_ref`` when none matches ``platform``, otherwise ``None``.

    ``None`` is returned too when the platform has no known architecture or the registry cannot be queried, so
    the caller proceeds with the pull. A returned list means the image must not be pulled for the platform.
    """
    arch = platform_to_oci_arch(platform)
    if not arch or image_ref.startswith(("/", ".")) or ("://" in image_ref and not image_ref.startswith("docker://")):
        return None
    available = registry_image_architectures(image_ref)
    if available is None or arch in available:
        return None
    log.warning(
        "Image '%s' is not published for architecture '%s' (platform '%s'), available: %s",
        image_ref,
        arch,
        platform,
        ", ".join(available),
    )
    return available
