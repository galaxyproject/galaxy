#!/usr/bin/env python
"""Recommend the most appropriate biocontainer for a list of conda packages.

Given a list of required packages (name + optional version) this resolves the
best matching ``quay.io/biocontainers`` image, verified against quay.io rather
than guessed. It reuses the existing mulled machinery (:mod:`.util` and
:mod:`.mulled_search`) and is deliberately free of any LLM/agent dependency so
it can be reused as a plain library or from the command line.

Examples::

    mulled-recommend samtools=1.17
    mulled-recommend bwa,samtools
    mulled-recommend --json "samtools=1.3.1,bedtools=2.26.0"
"""

import argparse
import itertools
import json
import logging
import sys
import threading
import time
from collections.abc import Sequence
from dataclasses import (
    dataclass,
    field,
)
from enum import Enum
from typing import (
    Any,
)

from requests import (
    HTTPError,
    RequestException,
    Session,
)

from galaxy.tool_util.deps.conda_util import CondaTarget
from galaxy.util import requests
from .util import (
    build_target,
    find_remote_mulled_name,
    mulled_tags_for,
    MulledNameMatch,
    select_mulled_v2_tag,
    split_tag,
    v2_image_name,
)

log = logging.getLogger(__name__)

BIOCONTAINERS_NAMESPACE = "biocontainers"
QUAY_BIOCONTAINERS_PREFIX = "quay.io/biocontainers"
RECOMMENDATION_CACHE_EXPIRY = 300  # seconds, mirrors QUAY_VERSIONS_CACHE_EXPIRY
# Bounds for version resolution: how many recent versions to try per unpinned
# package, and a hard cap on total combinations to test (keeps the search cheap
# even with several unpinned packages).
MAX_VERSION_CANDIDATES = 8
MAX_VERSION_COMBOS = 256


class RecommendationSource(str, Enum):
    QUAY_SINGLE = "quay_single"
    QUAY_MULLED_V2 = "quay_mulled_v2"
    NONE = "none"


class MatchQuality(str, Enum):
    EXACT_VERSION = "exact_version"
    NAME_ONLY = "name_only"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class PackageSpec:
    """A single required package: a name and an optional pinned version."""

    name: str
    version: str | None = None


@dataclass(frozen=True)
class ContainerRecommendation:
    """Result of a biocontainer lookup.

    ``image`` is a fully-qualified container reference (e.g.
    ``quay.io/biocontainers/samtools:1.17--h00cdaf9_0``) or ``None`` when
    nothing was found. ``match_quality`` distinguishes an exact-version hit
    from a name-only fallback; callers should only auto-apply an
    ``EXACT_VERSION`` recommendation.
    """

    image: str | None
    source: RecommendationSource
    match_quality: MatchQuality
    packages: tuple[PackageSpec, ...]
    multi_package: bool
    tag: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def found(self) -> bool:
        return self.image is not None


def _no_recommendation(packages: Sequence[PackageSpec], multi_package: bool, note: str) -> ContainerRecommendation:
    return ContainerRecommendation(
        image=None,
        source=RecommendationSource.NONE,
        match_quality=MatchQuality.NOT_FOUND,
        packages=tuple(packages),
        multi_package=multi_package,
        notes=(note,),
    )


# --- public entry point -----------------------------------------------------


# Per-process, bounded TTL memoization (no cross-worker sharing). Bounds repeated
# identical lookups (e.g. refine round-trips); pass use_cache=False to bypass.
class _TTLCache:
    """Minimal bounded TTL cache, hand-rolled so the lean ``galaxy-tool-util`` package
    needs no ``cachetools`` runtime dependency. Not thread-safe; guarded by ``_cache_lock``.
    """

    def __init__(self, maxsize: int, ttl: float) -> None:
        self._maxsize = maxsize
        self._ttl = ttl
        self._entries: dict[Any, tuple[float, ContainerRecommendation]] = {}

    def get(self, key: Any) -> ContainerRecommendation | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            self._entries.pop(key, None)
            return None
        return value

    def __setitem__(self, key: Any, value: ContainerRecommendation) -> None:
        if key not in self._entries and len(self._entries) >= self._maxsize:
            # Evict the entry closest to expiry to stay within ``maxsize``.
            soonest = min(self._entries, key=lambda k: self._entries[k][0])
            self._entries.pop(soonest, None)
        self._entries[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        self._entries.clear()


_cache = _TTLCache(maxsize=128, ttl=RECOMMENDATION_CACHE_EXPIRY)
_cache_lock = threading.Lock()


def _cache_key(packages: Sequence[PackageSpec]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((p.name, p.version or "") for p in packages))


def _normalize(packages: Sequence[PackageSpec]) -> list[PackageSpec]:
    normalized = []
    for p in packages:
        name = p.name.strip().lower()
        version = p.version.strip() if p.version else None
        normalized.append(PackageSpec(name, version or None))
    return normalized


def recommend_container(
    packages: Sequence[PackageSpec],
    *,
    session: Session | None = None,
    use_cache: bool = True,
    resolve_versions: bool = True,
) -> ContainerRecommendation:
    """Resolve the best ``quay.io/biocontainers`` image for ``packages``.

    For multi-package requests where some (or all) packages are unpinned,
    ``resolve_versions`` (default on) looks up candidate versions for the
    unpinned packages and searches for a version combination that is actually
    built, so a mixed request like ``samtools=1.17,bwa`` can still resolve to an
    exact mulled-v2 image instead of a name-only match. Set it false to skip the
    extra lookups.

    Never raises for a missing container or a transient network failure -- a
    ``NONE`` recommendation (with an explanatory note) is returned instead, so
    callers can degrade gracefully.
    """
    normalized = _normalize([p for p in packages if p.name])
    if not normalized:
        return _no_recommendation(normalized, False, "no packages supplied")

    key = (_cache_key(normalized), resolve_versions)
    if use_cache:
        with _cache_lock:
            hit = _cache.get(key)  # None once the TTLCache entry has expired
            if hit is not None:
                return hit

    owns_session = session is None
    if session is None:
        session = requests.Session()
    try:
        if len(normalized) == 1:
            recommendation = _recommend_single(normalized[0], session)
        else:
            recommendation = _recommend_multi(normalized, session, resolve_versions=resolve_versions)
    except RequestException as e:
        log.info("biocontainer lookup failed for %s: %s", key, e)
        recommendation = _no_recommendation(normalized, len(normalized) > 1, f"lookup failed: {e}")
    finally:
        if owns_session:
            session.close()

    if use_cache:
        with _cache_lock:
            _cache[key] = recommendation
    return recommendation


def biocontainer_tag_built(image: str, *, session: Session | None = None) -> bool | None:
    """Tri-state check of whether a ``quay.io/biocontainers`` image's exact tag is built.

    Returns:

    - ``True``  -- the tag is among the repository's built tags.
    - ``False`` -- the repository has tags, but not this one (the reference names
      a build/version that was never published, e.g. a hallucinated
      ``--py311h1128e8f_0`` build suffix).
    - ``None``  -- the answer can't be established: the reference isn't a
      ``quay.io/biocontainers`` image, it carries no tag, or the tag list
      couldn't be fetched (missing repo or transient network failure).

    Callers should only treat a ``False`` as grounds to override a container --
    ``None`` is deliberately conservative so a network blip or a non-biocontainer
    image is never mistaken for a broken reference. Never raises.
    """
    if not image:
        return None
    prefix = f"{QUAY_BIOCONTAINERS_PREFIX}/"
    if not image.startswith(prefix):
        return None
    ref = image[len(prefix) :]
    if ":" not in ref:
        return None
    repo, tag = ref.rsplit(":", 1)
    if not repo or not tag:
        return None

    owns_session = session is None
    if session is None:
        session = requests.Session()
    try:
        tags = mulled_tags_for(BIOCONTAINERS_NAMESPACE, repo, session=session)
    except (HTTPError, RequestException) as e:
        log.info("biocontainer tag verification failed for %s: %s", image, e)
        return None
    finally:
        if owns_session:
            session.close()

    # An empty list can't distinguish "repo absent" from a transient failure, so
    # don't claim the tag is missing -- only a populated list that excludes the
    # tag is positive evidence the reference is broken.
    if not tags:
        return None
    return tag in tags


def _lookup_exact_or_newest(targets: list[CondaTarget], session: Session) -> MulledNameMatch | None:
    """find_remote_mulled_name with the recommender's error handling.

    A 404 (HTTPError -- repo absent) is treated as "not found" (None); other network
    errors propagate to recommend_container's outer handler as a lookup failure.
    """
    try:
        return find_remote_mulled_name(
            targets, BIOCONTAINERS_NAMESPACE, "v2", allow_newest_fallback=True, session=session
        )
    except HTTPError:
        return None


def _recommend_single(spec: PackageSpec, session: Session) -> ContainerRecommendation:
    match = _lookup_exact_or_newest([build_target(spec.name, version=spec.version)], session)
    if match is None:
        return _no_recommendation([spec], False, f"no biocontainer found for '{spec.name}'")
    tag = match.name.split(":", 1)[1]
    notes: tuple[str, ...] = ()
    if spec.version and not match.exact:
        notes = (f"requested version {spec.version} not found; newest available tag is {tag}",)
    return ContainerRecommendation(
        image=f"{QUAY_BIOCONTAINERS_PREFIX}/{match.name}",
        source=RecommendationSource.QUAY_SINGLE,
        match_quality=MatchQuality.EXACT_VERSION if match.exact else MatchQuality.NAME_ONLY,
        packages=(spec,),
        multi_package=False,
        tag=tag,
        notes=notes,
    )


def _recommend_multi(
    specs: list[PackageSpec], session: Session, resolve_versions: bool = True
) -> ContainerRecommendation:
    versioned = [p for p in specs if p.version]

    # Fully pinned: the shared resolver gives the exact image (or newest fallback) in one probe.
    if len(versioned) == len(specs):
        match = _lookup_exact_or_newest([build_target(p.name, version=p.version) for p in specs], session)
        if match is None:
            return _no_recommendation(specs, True, f"no multi-package biocontainer built for {[p.name for p in specs]}")
        notes = () if match.exact else ("exact version combination not built; using newest available mulled-v2 build",)
        return ContainerRecommendation(
            image=f"{QUAY_BIOCONTAINERS_PREFIX}/{match.name}",
            source=RecommendationSource.QUAY_MULLED_V2,
            match_quality=MatchQuality.EXACT_VERSION if match.exact else MatchQuality.NAME_ONLY,
            packages=tuple(specs),
            multi_package=True,
            tag=match.name.split(":", 1)[1],
            notes=notes,
        )

    # Partial / unpinned: the mulled-v2 repo depends only on package names. Fetch its tags once,
    # then (optionally) resolve the unpinned versions against the tags that are actually built.
    repo = v2_image_name([build_target(p.name) for p in specs]).split(":")[0]
    try:
        tags = mulled_tags_for(BIOCONTAINERS_NAMESPACE, repo, session=session)
    except HTTPError:
        tags = []
    if not tags:
        return _no_recommendation(specs, True, f"no multi-package biocontainer built for {[p.name for p in specs]}")

    notes_list: list[str] = []
    version_hash: str | None = None
    if resolve_versions:
        resolved, version_hash = _resolve_versions(specs, tags, session)
        if resolved:
            unpinned = [p.name for p in specs if not p.version]
            notes_list.append("resolved version(s): " + ", ".join(f"{n}={resolved[n]}" for n in unpinned))
        else:
            notes_list.append("could not resolve a built version combination; using newest available build")
    elif versioned:
        notes_list.append("not all packages were versioned; resolved by package names only")

    if version_hash:
        tag, _ = select_mulled_v2_tag(tags, version_hash, allow_newest_fallback=True)
        quality = MatchQuality.EXACT_VERSION
    else:
        tag, quality = tags[0], MatchQuality.NAME_ONLY
    return ContainerRecommendation(
        image=f"{QUAY_BIOCONTAINERS_PREFIX}/{repo}:{tag}",
        source=RecommendationSource.QUAY_MULLED_V2,
        match_quality=quality,
        packages=tuple(specs),
        multi_package=True,
        tag=tag,
        notes=tuple(notes_list),
    )


def _candidate_versions(name: str, session: Session, limit: int) -> list[str]:
    """Recent biocontainer versions for a single package, newest first."""
    try:
        tags = mulled_tags_for(BIOCONTAINERS_NAMESPACE, name, session=session)
    except (HTTPError, RequestException):
        return []
    versions: list[str] = []
    for tag in tags:
        version = split_tag(tag)[0]
        if version not in versions:
            versions.append(version)
        if len(versions) >= limit:
            break
    return versions


def _resolve_versions(
    specs: list[PackageSpec],
    existing_tags: list[str],
    session: Session,
) -> tuple[dict[str, str] | None, str | None]:
    """Find a version combination whose mulled-v2 image is actually built.

    Pinned versions are fixed; unpinned packages contribute their recent
    versions. Returns the full ``{name: version}`` combination and its
    version-hash for the first combination present in ``existing_tags``, or
    ``(None, None)`` if none of the tried combinations is built.
    """
    existing_hashes = {tag.rsplit("-", 1)[0] for tag in existing_tags if "-" in tag}
    if not existing_hashes:
        return None, None

    candidate_lists: list[list[str]] = []
    for spec in specs:
        if spec.version:
            candidate_lists.append([spec.version])
        else:
            candidate_lists.append(_candidate_versions(spec.name, session, MAX_VERSION_CANDIDATES))
    if any(not candidates for candidates in candidate_lists):
        return None, None

    # itertools.product yields the all-newest combination first.
    for count, combo in enumerate(itertools.product(*candidate_lists)):
        if count >= MAX_VERSION_COMBOS:
            break
        targets = [build_target(spec.name, version=version) for spec, version in zip(specs, combo)]
        version_hash = v2_image_name(targets).split(":")[1]
        if version_hash in existing_hashes:
            return {spec.name: version for spec, version in zip(specs, combo)}, version_hash
    return None, None


# --- CLI --------------------------------------------------------------------


def _specs_from_arg(targets_raw: str) -> list[PackageSpec]:
    # Lazy import: mulled_build pulls in heavy build tooling. Keeping it out of
    # module scope lets the agent import path stay lightweight; it's only needed
    # for the CLI's spec parsing.
    from .mulled_build import target_str_to_targets

    return [PackageSpec(t.package, t.version) for t in target_str_to_targets(targets_raw)]


def main(argv: list[str] | None = None) -> None:
    """Main entry-point for the ``mulled-recommend`` CLI tool."""
    parser = argparse.ArgumentParser(
        description="Recommend the best quay.io/biocontainers image for a list of conda packages."
    )
    parser.add_argument(
        "targets",
        metavar="TARGETS",
        help="Comma-separated packages, each 'name' or 'name=version' (e.g. 'samtools=1.17,bedtools').",
    )
    parser.add_argument("-j", "--json", dest="as_json", action="store_true", help="Emit the recommendation as JSON.")
    parser.add_argument(
        "--no-resolve-versions",
        dest="resolve_versions",
        action="store_false",
        help="Don't look up versions for unpinned packages in multi-package requests.",
    )
    args = parser.parse_args(argv)

    recommendation = recommend_container(
        _specs_from_arg(args.targets), use_cache=False, resolve_versions=args.resolve_versions
    )

    if args.as_json:
        print(
            json.dumps(
                {
                    "image": recommendation.image,
                    "source": recommendation.source.value,
                    "match_quality": recommendation.match_quality.value,
                    "multi_package": recommendation.multi_package,
                    "tag": recommendation.tag,
                    "notes": list(recommendation.notes),
                }
            )
        )
        return

    if recommendation.found:
        print(recommendation.image)
        print(f"  match: {recommendation.match_quality.value} (source: {recommendation.source.value})")
    else:
        print("No biocontainer found.", file=sys.stderr)
    for note in recommendation.notes:
        print(f"  note: {note}", file=sys.stderr)


__all__ = (
    "ContainerRecommendation",
    "MatchQuality",
    "PackageSpec",
    "RecommendationSource",
    "main",
    "recommend_container",
)

if __name__ == "__main__":
    main()
