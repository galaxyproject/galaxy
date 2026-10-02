"""Curated workflow catalog: a slim on-disk projection of the IWC manifest.

The manifest published at iwc.galaxyproject.org is ~15 MB of JSON, far too
much to parse on a request thread or to retain in every web worker. This
module projects it down to the fields a card needs plus each workflow's tool ids (~250 KB),
writes that projection to disk, and serves it back from an in-process cache
keyed on the file's identity. Reading is pure disk I/O; the network is only
ever touched by the celery-beat task or by a single-flight daemon thread that
no request thread waits on, and even then a HEAD usually settles it without
transferring the body.

Deliberately trans-free and database-free so it unit-tests without either.
The module-level cache and refresh state deliberately follow the GTN search
DB pattern (``galaxy.agents.gtn.search``).
"""

import fcntl
import json
import logging
import os
import threading
import urllib.parse
import uuid
from collections import Counter
from collections.abc import (
    Callable,
    Iterable,
    Iterator,
)
from datetime import datetime
from pathlib import Path
from time import (
    monotonic,
    time,
)
from typing import (
    Any,
    Literal,
    NamedTuple,
    Protocol,
)

from galaxy.util.sanitize_html import sanitize_html
from galaxy.util.search import (
    filter_terms,
    FilteredTerm,
    parse_filters_structured,
    ParsedSearch,
    RawTextTerm,
)
from galaxy.workflow import iwc_manifest

log = logging.getLogger(__name__)

# Bumped whenever the entry shape changes: load_projection treats any other
# version as missing, so the next refresh re-downloads rather than HEAD-skipping.
CURATED_PROJECTION_VERSION = 2
IWC_WORKFLOW_URL_TEMPLATE = "https://iwc.galaxyproject.org/workflow/{iwc_id}/"
# A full URL rather than a TrsProxy server id: a custom trs_servers_config_file
# replaces the default server list wholesale, so an instance can lack the
# "dockstore" id while URL imports keep working.
DOCKSTORE_TRS_VERSION_URL_TEMPLATE = "https://dockstore.org/api/ga4gh/trs/v2/tools/{tool_id}/versions/{version_id}"
IWC_BRANCH_VERSION = "main"
REFRESH_COOLDOWN_SECONDS = 300.0
DEFAULT_FETCH_TIMEOUT_SECONDS = 30.0
CURATED_SEARCH_FILTERS = {
    "name": "name",
    "n": "name",
    "tag": "tag",
    "t": "tag",
    "collection": "collection",
    "c": "collection",
}
# ``filter_terms`` only caps unquoted raw terms, and the endpoint is anonymous, so
# without this a long run of ``name:x`` terms becomes one SQL predicate each in
# local-owner mode -- enough to overflow SQLite's expression tree.
MAX_CURATED_SEARCH_TERMS = 10

# path -> ((mtime_ns, inode, size), entries)
_projection_cache: dict[str, tuple[tuple[int, int, int], list[dict[str, Any]]]] = {}
_cache_lock = threading.Lock()

_refresh_lock = threading.Lock()
_refresh_in_flight = False
# -inf, not 0: monotonic() is time since boot on Linux, so a zero baseline would
# suppress the very first refresh on any host that has been up for less than the
# cooldown -- exactly the freshly-started container this cold-start path serves.
_last_refresh_attempt = float("-inf")


def _as_text(value: Any) -> str | None:
    """Coerce a manifest scalar to a string, dropping anything else."""
    if value is None or isinstance(value, (dict, list)):
        return None
    return str(value)


def _as_text_list(value: Any) -> list[str]:
    """Coerce a manifest sequence to a list of strings, dropping the rest."""
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _as_text(item)) is not None]


def _as_timestamp(value: Any) -> str | None:
    """Return a normalized ISO 8601 string, or None if the value isn't a date.

    Normalized rather than passed through: ``fromisoformat`` accepts forms the
    response model then rejects (``2024-W01-1`` among them), and a single such
    entry would 500 the whole endpoint. Re-emitting what the parser produced
    keeps the projection to the subset both agree on -- which also keeps these
    lexically comparable, since sorting relies on that.
    """
    text = _as_text(value)
    if text is None:
        return None
    # Python 3.10's fromisoformat rejects the "Z" UTC suffix that 3.11+ accepts.
    if text.endswith(("Z", "z")):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _dockstore_trs_url(trs_id: str, version_id: str) -> str:
    # quote_plus, as TrsServer.get_trs_url does, so this is the same URL an
    # import by server id would have recorded.
    return DOCKSTORE_TRS_VERSION_URL_TEMPLATE.format(
        tool_id=urllib.parse.quote_plus(trs_id), version_id=urllib.parse.quote_plus(version_id)
    )


def _trs_urls(trs_id: str | None, release: str | None) -> tuple[str | None, str | None]:
    """Return the (pinned, fallback) TRS URLs for a manifest entry.

    Pinned to the ``v{release}`` tag the card advertises -- which is also what
    the IWC site's own "Run in Galaxy" link imports. The branch would pull a
    moving tip, and because TRS imports dedup per user on (tool id, version) a
    user who imported it once would get that stale copy back on every later
    click. The branch URL is kept as a fallback because Dockstore sometimes
    lags a release tag behind the manifest.
    """
    if not trs_id:
        return None, None
    branch_url = _dockstore_trs_url(trs_id, IWC_BRANCH_VERSION)
    if not release:
        return branch_url, None
    return _dockstore_trs_url(trs_id, f"v{release}"), branch_url


def extract_tool_ids(definition: dict[str, Any]) -> list[str] | None:
    """Return the distinct tool ids a workflow definition's steps use, sorted.

    Walks subworkflows too, since their tools have to be installed just the same:
    both inline ones and ``#``/``$`` references into the definition's own
    ``subworkflows`` map, which is how the workflow importer resolves them. None
    means unknown -- a subworkflow referenced by URL, TRS id or database id, or a
    dangling reference, can't be resolved offline, and a partial list would let
    the card claim the workflow runs here. Iterative rather than recursive so a
    pathologically nested definition can't blow the stack on the refresh thread,
    and each definition is visited once so a self-referencing map terminates.
    """
    tool_ids: set[str] = set()
    visited: set[int] = set()
    pending = [definition]
    while pending:
        current = pending.pop()
        if id(current) in visited:
            continue
        visited.add(id(current))
        local_subworkflows = current.get("subworkflows")
        if not isinstance(local_subworkflows, dict):
            local_subworkflows = {}
        steps = current.get("steps")
        if isinstance(steps, dict):
            steps = list(steps.values())
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            tool_id = step.get("tool_id")
            if isinstance(tool_id, str) and tool_id:
                tool_ids.add(tool_id)
            subworkflow = step.get("subworkflow")
            if isinstance(subworkflow, dict):
                pending.append(subworkflow)
            elif step.get("type") == "subworkflow":
                content_id = step.get("content_id")
                referenced = None
                if not step.get("content_source") and isinstance(content_id, str) and content_id[:1] in ("#", "$"):
                    referenced = local_subworkflows.get(content_id[1:])
                if not isinstance(referenced, dict):
                    return None
                pending.append(referenced)
    return sorted(tool_ids)


def _iter_manifest_workflows(manifest: Any) -> Iterator[dict[str, Any]]:
    """Yield workflow objects from the manifest, skipping malformed containers.

    ``galaxy.agents.iwc.all_workflows`` assumes the manifest is well formed; here it is
    third-party input, and a repository that is not an object -- or a
    ``workflows`` value that is not a list -- must not take the whole
    projection down with it, since the projection is all-or-nothing.
    """
    if not isinstance(manifest, list):
        log.warning("IWC manifest is not a JSON array; skipping projection")
        return
    for repository in manifest:
        if not isinstance(repository, dict):
            log.debug("Skipping non-object IWC manifest repository entry")
            continue
        workflows = repository.get("workflows")
        if not isinstance(workflows, list):
            log.debug("Skipping IWC manifest repository with no workflows list: %s", repository.get("path"))
            continue
        for workflow in workflows:
            if not isinstance(workflow, dict):
                log.debug("Skipping non-object workflow in %s", repository.get("path"))
                continue
            yield workflow


def project_manifest(manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reduce the raw IWC manifest to the fields the curated tab renders.

    Every field is read defensively so a partially-populated -- or
    wrongly-typed -- manifest entry degrades to a sparse card rather than
    failing the whole projection or, worse, only failing later when the
    response model rejects it on a request thread.
    """
    entries: list[dict[str, Any]] = []
    for workflow in _iter_manifest_workflows(manifest):
        definition = workflow.get("definition")
        if not isinstance(definition, dict):
            definition = {}
        iwc_id = _as_text(workflow.get("iwcID"))
        # The top-level ``name`` is the descriptor stem -- literally "main" for
        # most entries -- so the human-facing name has to come from the
        # definition, and an entry without one is not renderable.
        name = _as_text(definition.get("name"))
        if not iwc_id or not name:
            log.debug("Skipping IWC manifest entry with no iwcID or definition name: %s", workflow.get("trsID"))
            continue
        # Name tags keep their ``name:`` prefix, matching what make_tag_string_list
        # produces for local rows. Stripping it here broke hashtag search: the
        # client's expandNameTag turns a clicked #tag back into ``tag:'name:...'``,
        # which could then never match. StatelessTags renders the prefix as '#'.
        tags = _as_text_list(definition.get("tags"))
        steps = definition.get("steps")
        release = _as_text(definition.get("release"))
        trs_url, trs_fallback_url = _trs_urls(_as_text(workflow.get("trsID")), release)
        entries.append(
            {
                "id": iwc_id,
                "name": name,
                # Sanitized at ingest because this is third-party content that
                # ends up in a v-html binding. Galaxy sanitizes locally-authored
                # annotations on write instead, which is what makes that binding
                # safe for every other card; the catalog has no such write path.
                "description": sanitize_html(_as_text(definition.get("annotation")) or ""),
                "tags": tags,
                # ``collections`` is the populated IWC grouping; ``categories``
                # is set on a small minority of entries.
                "collections": _as_text_list(workflow.get("collections")),
                "number_of_steps": len(steps) if isinstance(steps, dict) else 0,
                "update_time": _as_timestamp(workflow.get("updated")),
                "release": release,
                "doi": _as_text(workflow.get("doi")),
                "external_url": IWC_WORKFLOW_URL_TEMPLATE.format(iwc_id=iwc_id),
                "owner": None,
                "stored_workflow_id": None,
                "trs_url": trs_url,
                "trs_fallback_url": trs_fallback_url,
                # Full ids rather than short names: resolving them against the
                # toolbox is what tells a card whether it will run here. None
                # when a subworkflow can't be resolved offline.
                "tool_ids": extract_tool_ids(definition),
            }
        )
    return entries


def write_projection(path: str, entries: list[dict[str, Any]]) -> None:
    """Atomically write ``entries`` to ``path`` via a sibling tmp file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Scratch name is unique per write: web workers, the celery task and other
    # containers mounting the same directory all share this path, and a common
    # tmp name lets one writer truncate or publish another's half-written file.
    # Random rather than pid/thread based because containers routinely reuse
    # both. os.replace is atomic, so unique names are last-writer-wins.
    tmp_path = target.with_name(f"{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        with open(tmp_path, "w") as out:
            json.dump({"version": CURATED_PROJECTION_VERSION, "workflows": entries}, out)
        tmp_path.replace(target)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise


def load_projection(path: str) -> list[dict[str, Any]] | None:
    """Return the projected workflows at ``path``, or None if unusable.

    Performs no network I/O and no writes, so it is safe to call from a
    request thread. A missing, unreadable, malformed or wrong-version file all
    return None identically -- the next refresh replaces it either way.
    """
    try:
        stat = os.stat(path)
    except OSError:
        return None

    # Keyed on inode and size as well as the nanosecond mtime: publication is an
    # os.replace, so a new file has a new inode even when a coarse-resolution
    # filesystem hands back an unchanged timestamp for two writes in the same tick.
    identity = (stat.st_mtime_ns, stat.st_ino, stat.st_size)
    with _cache_lock:
        cached = _projection_cache.get(path)
        if cached is not None and cached[0] == identity:
            return cached[1]

    try:
        with open(path) as fh:
            payload = json.loads(fh.read())
    except (OSError, ValueError) as e:
        log.warning("Could not read curated workflow projection at %s: %s", path, e)
        return None

    if not isinstance(payload, dict):
        log.warning("Curated workflow projection at %s is not a JSON object", path)
        return None
    if payload.get("version") != CURATED_PROJECTION_VERSION:
        log.warning(
            "Curated workflow projection at %s has version %s, expected %s",
            path,
            payload.get("version"),
            CURATED_PROJECTION_VERSION,
        )
        return None
    entries = payload.get("workflows")
    if not isinstance(entries, list):
        log.warning("Curated workflow projection at %s has no workflows list", path)
        return None

    with _cache_lock:
        _projection_cache[path] = (identity, entries)
    return entries


def is_projection_stale(path: str, max_age_seconds: float) -> bool:
    """Whether ``path`` is older than ``max_age_seconds`` (missing counts as stale)."""
    if max_age_seconds <= 0:
        return False
    try:
        age = time() - os.stat(path).st_mtime
    except OSError:
        return True
    return age > max_age_seconds


class RefreshInProgress(Exception):
    """Another process holds the refresh lock and will publish the projection itself."""


def refresh_projection(path: str, timeout: float = DEFAULT_FETCH_TIMEOUT_SECONDS) -> int | None:
    """Refresh the projection at ``path``, downloading only when upstream changed.

    Returns the number of projected workflows, or None when the local copy was
    already current and nothing was downloaded. Raises ``RefreshInProgress``
    without touching the network when another process is already refreshing.
    Other exceptions propagate too -- the celery task and the background thread
    each decide how to report them.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Cross-process single flight. On a cold start or a projection-version bump
    # every web worker and celery would otherwise each pull and parse the 15 MB
    # manifest at once. flock rather than galaxy.util.filelock's O_EXCL lockfile:
    # the kernel drops it when the holder dies, so a killed worker can't wedge
    # refreshes forever. The lock file itself is never removed -- unlinking it
    # would let two processes lock different inodes of the "same" file.
    with open(target.with_name(f"{target.name}.lock"), "a") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RefreshInProgress(f"another process is already refreshing {path}") from None
        # Closing the file releases the lock.
        return _refresh_projection_locked(path, timeout)


def _refresh_projection_locked(path: str, timeout: float) -> int | None:
    target = Path(path)
    # Only skip the download when what we have is actually usable: a corrupt or
    # wrong-version file is exactly the case that must re-fetch, and asking
    # "modified since this file's mtime?" about it would answer no and strand it.
    current = load_projection(path)
    if current is not None and not iwc_manifest.manifest_modified_since(target.stat().st_mtime, timeout):
        # Nothing new upstream. Stamp the file so it stops looking stale, or every
        # subsequent request would re-arm this check until the manifest happens to
        # change -- turning a once-an-interval HEAD into a permanent poll.
        os.utime(target, None)
        log.debug("Curated catalog at %s is already current", path)
        return None

    manifest = iwc_manifest.download_manifest(timeout)
    entries = project_manifest(manifest)
    if not entries and current:
        # An upstream generation failure that returns HTTP 200 with an empty or
        # unparseable body would otherwise atomically replace a healthy catalog
        # with nothing, and the tab would look legitimately empty for an hour.
        raise ValueError(f"refusing to replace the curated catalog at {path} with an empty projection")
    write_projection(path, entries)
    return len(entries)


def request_background_refresh(path: str, timeout: float = DEFAULT_FETCH_TIMEOUT_SECONDS) -> bool:
    """Kick off a projection refresh on a daemon thread, at most one at a time.

    Returns True when a refresh is running (already in flight, or just
    started), False when the cooldown from a recent attempt is still active.
    The caller never waits: the lock is only held for the few instructions
    that update the single-flight state, and the network fetch happens
    entirely on the spawned thread.
    """
    global _refresh_in_flight, _last_refresh_attempt
    with _refresh_lock:
        if _refresh_in_flight:
            return True
        if monotonic() - _last_refresh_attempt < REFRESH_COOLDOWN_SECONDS:
            return False
        _refresh_in_flight = True
        _last_refresh_attempt = monotonic()
    threading.Thread(
        target=_background_refresh,
        args=(path, timeout),
        daemon=True,
        name="curated-workflows-refresh",
    ).start()
    return True


def _background_refresh(path: str, timeout: float) -> None:
    global _refresh_in_flight, _last_refresh_attempt
    try:
        count = refresh_projection(path, timeout)
        if count is None:
            log.debug("Curated catalog at %s was already current", path)
        else:
            log.info("Wrote %s curated workflows to %s", count, path)
    except RefreshInProgress:
        log.debug("Another process is refreshing the curated catalog at %s", path)
        # Not an attempt of ours, so it mustn't start the cooldown: requests that
        # land before the other process publishes should keep reporting
        # "preparing" (and retrying) rather than flipping to "unavailable".
        with _refresh_lock:
            _last_refresh_attempt = float("-inf")
    except Exception as e:
        log.warning("Could not refresh the curated workflow projection at %s: %s", path, e)
    finally:
        with _refresh_lock:
            _refresh_in_flight = False


class _Searchable:
    """An entry with its lowercased haystacks built once.

    Rebuilding the haystacks per (term, entry) pair made every term cost a pass
    of string building over the whole catalog; built once, the term loop is
    pure substring scanning.
    """

    __slots__ = ("entry", "name_text", "tags", "collections", "all_text")

    def __init__(self, entry: dict[str, Any]) -> None:
        name = str(entry.get("name") or "").lower()
        description = str(entry.get("description") or "").lower()
        self.entry = entry
        # Name alone, so ``name:`` means the same thing here, in local-owner mode
        # (which filters on StoredWorkflow.name), and on the other three tabs.
        # Annotations stay reachable through free text.
        self.name_text = name
        self.tags = [str(tag).lower() for tag in entry.get("tags") or []]
        self.collections = [str(collection).lower() for collection in entry.get("collections") or []]
        # Collections too, as on iwc.galaxyproject.org: "proteomics" should find the Proteomics collection.
        self.all_text = f"{name} {description} {' '.join(self.tags)} {' '.join(self.collections)}"


def parse_curated_search(search: str) -> ParsedSearch:
    """Parse a curated-tab search string, keeping at most ``MAX_CURATED_SEARCH_TERMS`` terms.

    Shared by the catalog filter below and ``WorkflowsManager.curated_index_query``
    so both modes accept exactly the same bounded query.
    """
    parsed = filter_terms(parse_filters_structured(search, CURATED_SEARCH_FILTERS))
    capped = ParsedSearch()
    for term in parsed.terms[:MAX_CURATED_SEARCH_TERMS]:
        if isinstance(term, FilteredTerm):
            capped.add_keyed_term(term.filter, term.text, term.quoted)
        else:
            capped.add_unfiltered_text(term.text, term.quoted)
    return capped


def search_curated(entries: list[dict[str, Any]], search: str | None) -> list[dict[str, Any]]:
    """Filter projected entries by a name/tag/collection search string, ANDing the terms."""
    if not search:
        return entries
    parsed = parse_curated_search(search)
    matched = [_Searchable(entry) for entry in entries]
    for term in parsed.terms:
        needle = term.text.lower()
        if isinstance(term, FilteredTerm):
            if term.filter == "name":
                matched = [item for item in matched if needle in item.name_text]
            elif term.filter == "tag":
                if term.quoted:
                    matched = [item for item in matched if needle in item.tags]
                else:
                    matched = [item for item in matched if any(needle in tag for tag in item.tags)]
            elif term.filter == "collection":
                if term.quoted:
                    matched = [item for item in matched if needle in item.collections]
                else:
                    matched = [item for item in matched if any(needle in c for c in item.collections)]
        elif isinstance(term, RawTextTerm):
            matched = [item for item in matched if needle in item.all_text]
    return [item.entry for item in matched]


class CuratedToolbox(Protocol):
    """The slice of ``ToolBox`` the missing-tools check reads."""

    @property
    def data_manager_tools(self) -> Iterable[str]: ...

    def has_tool(self, tool_id: str) -> bool: ...


def toolbox_availability(toolbox: CuratedToolbox, is_admin: bool) -> Callable[[str], bool]:
    """Whether a workflow using a tool id would run here for this user.

    Non-exact on purpose: a workflow imported through the UI runs with
    require_exact_tool_versions off, and ToolModule then binds any installed
    version of the same lineage (with a warning) -- so only a tool with no
    version installed at all stops it running. has_tool resolves from the
    toolbox's id and lineage maps (the index, on a CachedToolBox) without
    materialising tools.
    """
    return hide_data_manager_tools(toolbox.has_tool, toolbox.data_manager_tools, is_admin)


def find_missing_tools(
    entries: list[dict[str, Any]], tool_is_available: Callable[[str], bool]
) -> dict[str, list[str] | None]:
    """Map each entry id to the tool ids it needs that ``tool_is_available`` rejects.

    None means unknown -- an entry with no usable ``tool_ids`` list. Lookups are
    memoized for the call because the catalog shares most of its tools: ~1500
    references collapse to ~600 distinct ids.
    """
    available: dict[str, bool] = {}
    missing: dict[str, list[str] | None] = {}
    for entry in entries:
        tool_ids = entry.get("tool_ids")
        if not isinstance(tool_ids, list):
            missing[entry.get("id") or ""] = None
            continue
        entry_missing = []
        for tool_id in tool_ids:
            if not isinstance(tool_id, str):
                continue
            if tool_id not in available:
                available[tool_id] = tool_is_available(tool_id)
            if not available[tool_id]:
                entry_missing.append(tool_id)
        missing[entry.get("id") or ""] = entry_missing
    return missing


def hide_data_manager_tools(
    tool_is_available: Callable[[str], bool], data_manager_tool_ids: Iterable[str], is_admin: bool
) -> Callable[[str], bool]:
    """Wrap ``tool_is_available`` so data manager tools read as missing for non-admins.

    ``ToolBox.has_tool`` counts them as installed, but only an admin may run one
    (``DataManagerTool.allow_user_access``). Matched by lineage as well as exact
    id, like has_tool's own non-exact lookup. The toolbox registers data manager
    tools eagerly in ``data_manager_tools``, so this never loads a tool.
    """
    if is_admin:
        return tool_is_available
    restricted = {_tool_lineage(tool_id) for tool_id in data_manager_tool_ids}
    if not restricted:
        return tool_is_available

    def available(tool_id: str) -> bool:
        return _tool_lineage(tool_id) not in restricted and tool_is_available(tool_id)

    return available


def _tool_lineage(tool_id: str) -> str:
    # A guid (``host/repos/owner/repo/tool/version``) ends in its version; a
    # plain id like ``cat1`` has no version to strip and is its own lineage.
    return tool_id.rsplit("/", 1)[0] if "/" in tool_id else tool_id


def sort_curated(
    entries: list[dict[str, Any]],
    sort_by: str | None,
    sort_desc: bool | None,
    missing_tools: dict[str, list[str] | None] | None = None,
) -> list[dict[str, Any]]:
    """Order projected entries, defaulting to most-recently-updated first.

    When ``missing_tools`` is given and no explicit sort was asked for, entries
    that will run here as-is come first, each group keeping the default order.
    """
    ordered = _sort_curated(entries, sort_by, sort_desc)
    if sort_by is None and missing_tools is not None:
        # Stable, so the id tiebreaker inside each group survives and pagination
        # stays deterministic. Unknown counts as not runnable: no badge vouches for it.
        ordered.sort(key=lambda entry: missing_tools.get(entry.get("id") or "") != [])
    return ordered


def _sort_curated(entries: list[dict[str, Any]], sort_by: str | None, sort_desc: bool | None) -> list[dict[str, Any]]:
    descending = True if sort_desc is None else sort_desc
    # Every key ends in the id. Two thirds of the real catalog shares an
    # update_time, and a stable sort would otherwise fall back to manifest order
    # -- which the hourly refresh rewrites, so a tie group straddling a page
    # boundary would duplicate or drop cards between one page and the next. The
    # SQL path tie-breaks on StoredWorkflow.id for the same reason.
    if sort_by == "name":
        return sorted(
            entries, key=lambda entry: ((entry.get("name") or "").lower(), entry.get("id") or ""), reverse=descending
        )
    # ``update_time`` is an ISO 8601 string, so lexical order is chronological;
    # entries missing it sort last in either direction. ``create_time`` has no
    # separate projected value, so it shares this ordering.
    missing_last = "" if descending else "~"
    return sorted(
        entries,
        key=lambda entry: (entry.get("update_time") or missing_last, entry.get("id") or ""),
        reverse=descending,
    )


class CatalogPage(NamedTuple):
    """One page of the IWC catalog, or the reason there isn't one yet."""

    source: Literal["iwc", "preparing", "unavailable"]
    total_matches: int
    entries: list[dict[str, Any]]
    collections: list[tuple[str, int]]


def count_collections(entries: list[dict[str, Any]]) -> list[tuple[str, int]]:
    """Every collection in ``entries`` with its size, largest first, as the IWC site lists them."""
    counts = Counter(collection for entry in entries for collection in entry.get("collections") or [])
    return sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))


def list_catalog(
    path: str,
    *,
    search: str | None,
    sort_by: str | None,
    sort_desc: bool | None,
    offset: int,
    limit: int,
    max_age_seconds: float,
    toolbox: CuratedToolbox | None = None,
    is_admin: bool = False,
) -> CatalogPage:
    """Search, sort and page the projection at ``path`` for one request.

    Never performs network I/O. A missing projection kicks the background
    refresh and reports ``preparing`` (or ``unavailable`` while the cooldown
    from a failed attempt is still running) with no entries. Each returned
    entry carries ``missing_tools`` as checked against ``toolbox`` for this
    user, or None throughout when there is no toolbox to check against.
    Collection counts cover the whole catalog, not just the matches, so the
    choices on offer don't shift under a search.
    """
    entries = load_projection(path)
    if entries is None:
        started = request_background_refresh(path)
        return CatalogPage("preparing" if started else "unavailable", 0, [], [])

    # Serve what we have and refresh behind it when it has aged out. Without
    # this the projection is only ever written on a cold start, so a Galaxy
    # running no celery beat would pin whatever catalog it happened to fetch
    # first and never notice a newer one. The refresh is single-flight,
    # cooldown-guarded, and skips the download unless upstream actually moved.
    if is_projection_stale(path, max_age_seconds):
        request_background_refresh(path)

    matched = search_curated(entries, search)
    missing = find_missing_tools(matched, toolbox_availability(toolbox, is_admin)) if toolbox is not None else None
    ordered = sort_curated(matched, sort_by, sort_desc, missing)
    page = [
        {**entry, "missing_tools": (missing or {}).get(entry.get("id") or "")}
        for entry in ordered[offset : offset + limit]
    ]
    return CatalogPage("iwc", len(ordered), page, count_collections(entries))


def clear_caches() -> None:
    """Drop the projection cache and reset background-refresh state. Tests use this."""
    global _refresh_in_flight, _last_refresh_attempt
    with _cache_lock:
        _projection_cache.clear()
    with _refresh_lock:
        _refresh_in_flight = False
        _last_refresh_attempt = float("-inf")
