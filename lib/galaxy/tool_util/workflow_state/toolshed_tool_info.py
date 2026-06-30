"""GetToolInfo implementation that fetches ParsedTool from ToolShed 2.0 API.

Supports the full Galaxy workflow tool_id format:
  toolshed.g2.bx.psu.edu/repos/owner/repo/tool_id/version

Converts to TRS-style API call:
  GET {toolshed_url}/api/tools/{owner~repo~tool_id}/versions/{version}

Results are cached locally as JSON files with an index for provenance tracking.
Cache can be populated from multiple sources: ToolShed API, Galaxy instance API, or local XML.
"""

import hashlib
import json
import logging
import os
from datetime import (
    datetime,
    timezone,
)
from typing import (
    Any,
)
from urllib.parse import quote

from galaxy.tool_util_models import ParsedTool

log = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".galaxy", "tool_info_cache")
CACHE_DIR_ENV_VAR = "GALAXY_TOOL_CACHE_DIR"
DEFAULT_TOOLSHED_URL = "https://toolshed.g2.bx.psu.edu"
TOOLSHED_URL_ENV_VAR = "GALAXY_TOOLSHED_URL"


def get_cache_dir(override: str | None = None) -> str:
    """Return cache directory from override, env var, or default."""
    return override or os.environ.get(CACHE_DIR_ENV_VAR) or DEFAULT_CACHE_DIR


GALAXY_URL_ENV_VAR = "GALAXY_URL"
DEFAULT_GALAXY_URL = "https://usegalaxy.org"


def parse_toolshed_tool_id(tool_id: str) -> tuple[str, str, str | None] | None:
    """Parse a toolshed tool_id into (toolshed_url, trs_tool_id, tool_version).

    Input format: toolshed.g2.bx.psu.edu/repos/owner/repo/tool_id/version
    Or with scheme: https://toolshed.g2.bx.psu.edu/repos/owner/repo/tool_id/version

    Returns None if the tool_id is not a toolshed tool.
    """
    if "/repos/" not in tool_id:
        return None

    parts = tool_id.split("/repos/", 1)
    toolshed_base = parts[0]
    rest = parts[1]

    # rest is: owner/repo/tool_id/version (or owner/repo/tool_id without version)
    segments = rest.split("/")
    if len(segments) < 3:
        return None

    # owner/repo/tool_id are the TRS tool ID components
    owner = segments[0]
    repo = segments[1]
    tool_id_segment = segments[2]
    trs_tool_id = f"{owner}~{repo}~{tool_id_segment}"

    # Version may be the 4th segment or provided separately
    tool_version = segments[3] if len(segments) > 3 else None

    # Ensure toolshed base has a scheme
    if not toolshed_base.startswith("http"):
        toolshed_base = f"https://{toolshed_base}"

    return toolshed_base, trs_tool_id, tool_version


def _cache_key(toolshed_url: str, trs_tool_id: str, tool_version: str) -> str:
    """Generate a filesystem-safe cache key."""
    raw = f"{toolshed_url}/{trs_tool_id}/{tool_version}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _tool_id_from_trs(toolshed_url: str, trs_tool_id: str) -> str:
    """Reconstruct a readable tool_id from toolshed_url and trs_tool_id."""
    # trs_tool_id is owner~repo~tool_id
    parts = trs_tool_id.split("~")
    # Strip scheme for display
    base = toolshed_url.replace("https://", "").replace("http://", "")
    return f"{base}/repos/{'/'.join(parts)}"


class CacheIndex:
    """Manages the index.json file that tracks provenance of cached tools."""

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        self._index_path = os.path.join(cache_dir, "index.json")
        self._entries: dict | None = None

    @property
    def entries(self) -> dict:
        if self._entries is None:
            self._entries = self._load()
        return self._entries

    def _load(self) -> dict:
        if not os.path.exists(self._index_path):
            return {}
        try:
            with open(self._index_path) as f:
                data = json.load(f)
            return data.get("entries", {})
        except Exception:
            log.debug(f"Cache index {self._index_path} invalid, starting fresh")
            return {}

    def _save(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(self._index_path, "w") as f:
            json.dump({"entries": self.entries}, f, indent=2)

    def add(self, cache_key: str, tool_id: str, tool_version: str, source: str, source_url: str = ""):
        self.entries[cache_key] = {
            "tool_id": tool_id,
            "tool_version": tool_version,
            "source": source,
            "source_url": source_url,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save()

    def remove(self, cache_key: str):
        if cache_key in self.entries:
            del self.entries[cache_key]
            self._save()

    def has(self, cache_key: str) -> bool:
        return cache_key in self.entries

    def list_all(self) -> list[dict]:
        """Return all index entries with their cache keys."""
        result = []
        for key, entry in self.entries.items():
            result.append({"cache_key": key, **entry})
        return result

    def clear(self):
        self._entries = {}
        self._save()


class ToolShedGetToolInfo:
    """Fetches ParsedTool from ToolShed 2.0 API with local filesystem cache."""

    def __init__(
        self,
        cache_dir: str | None = None,
        default_toolshed_url: str | None = None,
        galaxy_url: str | None = None,
    ):
        self.cache_dir = get_cache_dir(cache_dir)
        self.default_toolshed_url = default_toolshed_url or os.environ.get(TOOLSHED_URL_ENV_VAR) or DEFAULT_TOOLSHED_URL
        self.galaxy_url = galaxy_url or os.environ.get(GALAXY_URL_ENV_VAR) or DEFAULT_GALAXY_URL
        self._memory_cache: dict[str, ParsedTool] = {}
        self._index = CacheIndex(self.cache_dir)

    @property
    def index(self) -> CacheIndex:
        return self._index

    def resolve_tool_coordinates(self, tool_id: str, tool_version: str | None):
        """Public accessor for resolved (toolshed_url, trs_tool_id, version, readable_id)."""
        return self._resolve_tool_coordinates(tool_id, tool_version)

    def _resolve_tool_coordinates(self, tool_id: str, tool_version: str | None):
        """Resolve tool_id to (toolshed_url, trs_tool_id, version, readable_id).

        Handles both toolshed tools (/repos/ in ID) and stock tools (simple ID).
        """
        parsed = parse_toolshed_tool_id(tool_id)
        if parsed is not None:
            toolshed_url, trs_tool_id, embedded_version = parsed
            version = tool_version or embedded_version
            readable_id = _tool_id_from_trs(toolshed_url, trs_tool_id)
        else:
            # Stock tool — use default toolshed URL and tool_id as TRS ID
            toolshed_url = self.default_toolshed_url
            trs_tool_id = tool_id
            version = tool_version or "_default_"
            readable_id = tool_id
        return toolshed_url, trs_tool_id, version, readable_id

    def get_tool_info(self, tool_id: str, tool_version: str | None) -> ParsedTool | None:
        toolshed_url, trs_tool_id, version, readable_id = self._resolve_tool_coordinates(tool_id, tool_version)
        if version is None:
            raise KeyError(f"No version available for tool: {tool_id}")

        cache_key = _cache_key(toolshed_url, trs_tool_id, version)

        # Check memory cache
        if cache_key in self._memory_cache:
            return self._memory_cache[cache_key]

        # Check filesystem cache
        cached = self._load_from_cache(cache_key)
        if cached is not None:
            self._memory_cache[cache_key] = cached
            return cached

        # Fetch from API
        parsed_tool = self._fetch_from_api(toolshed_url, trs_tool_id, version)
        readable_id = _tool_id_from_trs(toolshed_url, trs_tool_id)
        self._save_to_cache(
            cache_key,
            parsed_tool,
            readable_id,
            version,
            source="api",
            source_url=f"{toolshed_url}/api/tools/{trs_tool_id}/versions/{version}",
        )
        self._memory_cache[cache_key] = parsed_tool
        return parsed_tool

    def populate_from_parsed_tool(
        self,
        tool_id: str,
        tool_version: str,
        parsed_tool: ParsedTool,
        source: str = "local",
        source_url: str = "",
    ) -> str:
        """Cache a ParsedTool directly. Returns the cache key."""
        toolshed_url, trs_tool_id, version, readable_id = self._resolve_tool_coordinates(tool_id, tool_version)
        if version is None:
            raise ValueError(f"No version for: {tool_id}")

        cache_key = _cache_key(toolshed_url, trs_tool_id, version)
        self._save_to_cache(cache_key, parsed_tool, readable_id, version, source, source_url)
        self._memory_cache[cache_key] = parsed_tool
        return cache_key

    def has_cached(self, tool_id: str, tool_version: str | None = None) -> bool:
        """Check if a tool is in the cache (filesystem or memory)."""
        toolshed_url, trs_tool_id, version, _readable_id = self._resolve_tool_coordinates(tool_id, tool_version)
        if version is None:
            return False
        cache_key = _cache_key(toolshed_url, trs_tool_id, version)
        return cache_key in self._memory_cache or os.path.exists(self._cache_path(cache_key))

    def list_cached(self) -> list[dict]:
        """Return provenance info for all cached tools."""
        return self._index.list_all()

    def clear_cache(self, tool_id: str | None = None) -> int:
        """Clear cache. If tool_id given, clear matching entries; otherwise clear all.

        Returns the number of index entries removed.
        """
        if tool_id is None:
            entries = self._index.list_all()
            count = len(entries)
            for entry in entries:
                path = self._cache_path(entry["cache_key"])
                if os.path.exists(path):
                    os.remove(path)
            self._index.clear()
            self._memory_cache.clear()
            return count
        # Clear entries matching tool_id prefix
        to_remove = []
        for entry in self._index.list_all():
            if entry.get("tool_id", "").startswith(tool_id.rstrip("*")):
                to_remove.append(entry["cache_key"])
        for key in to_remove:
            path = self._cache_path(key)
            if os.path.exists(path):
                os.remove(path)
            self._index.remove(key)
            self._memory_cache.pop(key, None)
        return len(to_remove)

    def stat_cached(self, cache_key: str) -> dict[str, Any] | None:
        """Return filesystem stats for a cached entry, or None if no file exists."""
        path = self._cache_path(cache_key)
        if not os.path.exists(path):
            return None
        st = os.stat(path)
        return {
            "size_bytes": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
        }

    def load_cached_raw(self, cache_key: str) -> Any | None:
        """Load raw JSON contents (not ParsedTool-validated) for a cache entry."""
        path = self._cache_path(cache_key)
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return None

    def remove_cached(self, cache_key: str) -> bool:
        """Remove a single cached entry by key. Returns True if it existed."""
        existed = self._index.has(cache_key) or os.path.exists(self._cache_path(cache_key))
        path = self._cache_path(cache_key)
        if os.path.exists(path):
            os.remove(path)
        self._index.remove(cache_key)
        self._memory_cache.pop(cache_key, None)
        return existed

    def refetch(
        self,
        tool_id: str,
        tool_version: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Idempotent populate (force=False) or forced re-fetch (force=True).

        Returns {"cache_key": str, "fetched": bool, "already_cached": bool}.
        Raises KeyError when fetching fails.
        """
        toolshed_url, trs_tool_id, version, _readable = self._resolve_tool_coordinates(tool_id, tool_version)
        already_cached = False
        if version is not None:
            already_cached = self.has_cached(tool_id, version)
        if already_cached and not force:
            key = _cache_key(toolshed_url, trs_tool_id, version)
            return {"cache_key": key, "fetched": False, "already_cached": True}
        if already_cached and force and version is not None:
            key = _cache_key(toolshed_url, trs_tool_id, version)
            self.remove_cached(key)
        tool = self.get_tool_info(tool_id, tool_version)
        if tool is None:
            raise KeyError(f"Failed to fetch tool: {tool_id}")
        resolved_version = tool.version or version or "unknown"
        key = _cache_key(toolshed_url, trs_tool_id, resolved_version)
        return {"cache_key": key, "fetched": True, "already_cached": already_cached}

    def fetch_from_api(self, toolshed_url: str, trs_tool_id: str, tool_version: str) -> ParsedTool:
        """Fetch ParsedTool from ToolShed API (no caching)."""
        return self._fetch_from_api(toolshed_url, trs_tool_id, tool_version)

    def fetch_from_galaxy(self, galaxy_url: str, tool_id: str, tool_version: str | None = None) -> ParsedTool:
        """Fetch ParsedTool from a Galaxy instance's /api/tools/{id}/parsed endpoint."""
        import requests

        encoded_id = quote(tool_id, safe="")
        url = f"{galaxy_url}/api/tools/{encoded_id}/parsed"
        params = {}
        if tool_version:
            params["tool_version"] = tool_version
        log.info(f"Fetching tool info from Galaxy: {url}")
        response = requests.get(url, params=params, headers={"Accept": "application/json"}, timeout=30)
        if response.status_code != 200:
            raise KeyError(f"Failed to fetch tool from Galaxy {url}: {response.status_code} {response.text[:200]}")
        return ParsedTool.model_validate(response.json())

    def load_cached(self, cache_key: str) -> ParsedTool | None:
        """Load a ParsedTool from the filesystem cache by key."""
        return self._load_from_cache(cache_key)

    def _fetch_from_api(self, toolshed_url: str, trs_tool_id: str, tool_version: str) -> ParsedTool:
        import requests

        url = f"{toolshed_url}/api/tools/{trs_tool_id}/versions/{tool_version}"
        log.info(f"Fetching tool info from {url}")
        response = requests.get(url, headers={"Accept": "application/json"}, timeout=30)
        if response.status_code != 200:
            raise KeyError(f"Failed to fetch tool info from {url}: {response.status_code} {response.text[:200]}")
        return ParsedTool.model_validate(response.json())

    def _cache_path(self, cache_key: str) -> str:
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    def _load_from_cache(self, cache_key: str) -> ParsedTool | None:
        path = self._cache_path(cache_key)
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            parsed_tool = ParsedTool.model_validate(data)
            # Backfill index if cache file exists without index entry
            if not self._index.has(cache_key):
                self._index.add(cache_key, data.get("id", "unknown"), data.get("version", "unknown"), source="unknown")
            return parsed_tool
        except Exception:
            log.debug(f"Cache entry {path} invalid, ignoring")
            return None

    def _save_to_cache(
        self,
        cache_key: str,
        parsed_tool: ParsedTool,
        tool_id: str,
        tool_version: str,
        source: str,
        source_url: str = "",
    ):
        os.makedirs(self.cache_dir, exist_ok=True)
        path = self._cache_path(cache_key)
        try:
            with open(path, "w") as f:
                f.write(parsed_tool.model_dump_json(indent=2))
        except Exception:
            log.debug(f"Failed to write cache entry {path}")
            return
        self._index.add(cache_key, tool_id, tool_version, source, source_url)


class CombinedGetToolInfo:
    """GetToolInfo that tries stock tools first, then falls back to ToolShed API."""

    def __init__(self, stock_get_tool_info, toolshed_get_tool_info: ToolShedGetToolInfo | None = None):
        self.stock = stock_get_tool_info
        self.toolshed = toolshed_get_tool_info or ToolShedGetToolInfo()

    def get_tool_info(self, tool_id: str, tool_version: str | None) -> ParsedTool | None:
        # If it looks like a toolshed tool, try toolshed first
        if "/repos/" in tool_id:
            try:
                return self.toolshed.get_tool_info(tool_id, tool_version)
            except KeyError:
                pass

        # Try stock tools
        return self.stock.get_tool_info(tool_id, tool_version)
