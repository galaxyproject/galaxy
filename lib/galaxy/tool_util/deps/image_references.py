"""Parse container image references and match them against an allowlist.

References are parsed into registry, repository, tag and digest and
canonicalized like the Docker CLI does (``python:3.13`` is
``docker.io/library/python:3.13``), so matching compares parsed parts rather
than string prefixes. ``registry-1.docker.io``, the host that serves Docker
Hub's registry API, is canonicalized to ``docker.io`` as well, which the
Docker CLI does not do, so a denied Docker Hub image cannot be named through it.
For the same reason an explicit default HTTPS port (``quay.io:443``) is dropped.

Allowlist entries: ``*`` allows anything; ``<registry-or-path>/*`` allows any
repository below it, at any depth; ``<repository>`` allows any tag or digest of
it; ``<repository>:<tag>`` only that tag, without a digest; and
``<repository>@<digest>`` only that digest, whatever the tag. Runtimes pull the
digest of a reference that has both and ignore its tag, so a tag entry must not
allow ``<repository>:<tag>@<any digest>``.

Denied entries take precedence over allowed ones and are limited to
``<registry-or-path>/*`` and ``<repository>``: the same image can always be
named by another tag or digest, so denying one would block nothing.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

DOCKER_HUB = "docker.io"
DOCKER_HUB_ALIASES = frozenset({"docker.io", "index.docker.io", "registry-1.docker.io"})
DOCKER_SCHEME = "docker://"

# Grammar from https://github.com/distribution/reference, without IPv6 hosts.
_DOMAIN_COMPONENT = r"(?:[a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9])"
_REGISTRY_RE = re.compile(rf"{_DOMAIN_COMPONENT}(?:\.{_DOMAIN_COMPONENT})*(?::[0-9]+)?")
_PATH_COMPONENT_RE = re.compile(r"[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*")
_TAG_RE = re.compile(r"\w[\w.-]{0,127}", re.ASCII)
_DIGEST_RE = re.compile(r"sha256:[a-f0-9]{64}|sha512:[a-f0-9]{128}")


class ImageReferenceError(ValueError):
    """Raised for a string that is not a container image reference or allowlist entry."""


@dataclass(frozen=True)
class ImageReference:
    registry: str
    repository: str
    tag: str | None = None
    digest: str | None = None


def _split_name(value: str, name: str, namespace: bool = False) -> tuple[str, str]:
    """Split ``name`` into canonical (registry, repository path)."""
    components = name.split("/")
    # In a namespace entry a lone registry (``quay.io/*``) stands for the whole registry.
    if (len(components) > 1 or namespace) and (
        "." in components[0] or ":" in components[0] or components[0] == "localhost"
    ):
        if not _REGISTRY_RE.fullmatch(components[0]):
            raise ImageReferenceError(f"'{value}' has an invalid registry '{components[0]}'")
        # Registries are served over HTTPS, so an explicit :443 names the same registry.
        registry = components[0].lower().removesuffix(":443")
        registry = DOCKER_HUB if registry in DOCKER_HUB_ALIASES else registry
        components = components[1:]
    else:
        registry = DOCKER_HUB
    for component in components:
        if not _PATH_COMPONENT_RE.fullmatch(component):
            raise ImageReferenceError(f"'{value}' has an invalid repository path component '{component}'")
    if registry == DOCKER_HUB and len(components) == 1 and not namespace:
        components = ["library", *components]
    return registry, "/".join(components)


def _strip_scheme(value: str) -> str:
    if not value or any(c.isspace() for c in value):
        raise ImageReferenceError(f"'{value}' is not a container image reference")
    if value.startswith(DOCKER_SCHEME):
        return value[len(DOCKER_SCHEME) :]
    if "://" in value:
        # oras://, library://, shub:// ... are not served by a Docker registry.
        raise ImageReferenceError(f"'{value}' uses an unsupported scheme, only docker:// references are supported")
    return value


def parse_image_reference(value: str) -> ImageReference:
    """Parse and canonicalize a Docker image reference, raising :class:`ImageReferenceError` otherwise."""
    name = _strip_scheme(value)
    name, at, digest = name.partition("@")
    if at and not _DIGEST_RE.fullmatch(digest):
        raise ImageReferenceError(f"'{value}' has an invalid digest '{digest}'")
    tag = None
    colon = name.rfind(":")
    if colon > name.rfind("/"):
        name, tag = name[:colon], name[colon + 1 :]
        if not _TAG_RE.fullmatch(tag):
            raise ImageReferenceError(f"'{value}' has an invalid tag '{tag}'")
    registry, repository = _split_name(value, name)
    return ImageReference(registry, repository, tag, digest or None)


@dataclass(frozen=True)
class _Entry:
    reference: ImageReference
    # The reference's repository is a path prefix ("" for a whole registry).
    namespace: bool = False

    def matches(self, reference: ImageReference) -> bool:
        entry = self.reference
        if reference.registry != entry.registry:
            return False
        if self.namespace:
            return not entry.repository or reference.repository.startswith(f"{entry.repository}/")
        if reference.repository != entry.repository:
            return False
        if entry.digest:
            return reference.digest == entry.digest
        if entry.tag:
            return reference.digest is None and reference.tag == entry.tag
        return True


def _parse_entry(entry: str) -> _Entry:
    if not isinstance(entry, str):
        raise ImageReferenceError(f"container allowlist entry {entry!r} is not a string")
    namespace = entry.endswith("/*")
    body = entry[:-2] if namespace else entry
    if "*" in body:
        raise ImageReferenceError(f"'{entry}' may only use '*' alone or as a trailing '/*'")
    if not namespace:
        return _Entry(parse_image_reference(entry))
    prefix = _strip_scheme(body) if body else ""
    if not prefix:
        raise ImageReferenceError(f"'{entry}' names no registry or path before '/*'")
    registry, path = _split_name(entry, prefix, namespace=True)
    return _Entry(ImageReference(registry, path), namespace=True)


def _parse_denied_entry(entry: str) -> _Entry:
    if entry == "*":
        raise ImageReferenceError("'*' cannot be denied, allow no images with an empty list of allowed containers")
    parsed = _parse_entry(entry)
    # A bare host parses as a Docker Hub image (``quay.io`` is docker.io/library/quay.io),
    # which would deny nothing on that registry.
    name = _strip_scheme(entry).partition("@")[0].partition(":")[0]
    if not parsed.namespace and "/" not in name and ("." in name or name == "localhost"):
        raise ImageReferenceError(f"'{entry}' names a registry, deny '{name}/*' to deny every image on it")
    if parsed.reference.tag or parsed.reference.digest:
        raise ImageReferenceError(
            f"'{entry}' names a tag or digest, deny the repository or namespace instead: "
            "the same image can be named by another tag or digest"
        )
    return parsed


class ContainerAllowlist:
    def __init__(self, entries: Iterable[str], denied: Iterable[str] = ()):
        self.raw_entries = tuple(entries)
        self.unrestricted = "*" in self.raw_entries
        self._rules = [_parse_entry(entry) for entry in self.raw_entries if entry != "*"]
        self._denied_rules = [_parse_denied_entry(entry) for entry in denied]

    def rejection(self, identifier: str) -> str | None:
        """Return why ``identifier`` is not allowed, or ``None`` if it is."""
        if self.unrestricted and not self._denied_rules:
            return None
        try:
            reference = parse_image_reference(identifier)
        except ImageReferenceError as e:
            return f"Invalid container: {e}"
        if any(rule.matches(reference) for rule in self._denied_rules):
            return f"Container '{identifier}' is denied for user defined tools on this Galaxy server."
        if self.unrestricted or any(rule.matches(reference) for rule in self._rules):
            return None
        return (
            f"Container '{identifier}' is not allowed for user defined tools on this Galaxy server. "
            f"Allowed containers: {self.describe()}"
        )

    def describe(self) -> str:
        return ", ".join(self.raw_entries) if self.raw_entries else "(none)"
