import json
import os
from typing import (
    Any,
    Dict,
    Optional,
)

RAW_CACHED_JSON = Dict[str, Any]


class ToolStateCache:
    _cache_directory: str

    def __init__(self, cache_directory: str):
        if not os.path.exists(cache_directory):
            os.makedirs(cache_directory)
        self._cache_directory = cache_directory

    def _cache_target(self, tool_id: str, tool_version: str):
        # consider breaking this into multiple directories...
        cache_target = os.path.join(self._cache_directory, tool_id, tool_version)
        return cache_target

    def get_cache_entry_for(self, tool_id: str, tool_version: str) -> Optional[RAW_CACHED_JSON]:
        cache_target = self._cache_target(tool_id, tool_version)
        if not os.path.exists(cache_target):
            return None
        with open(cache_target) as f:
            return json.load(f)

    def has_cached_entry_for(self, tool_id: str, tool_version: str) -> bool:
        cache_target = self._cache_target(tool_id, tool_version)
        return os.path.exists(cache_target)

    def insert_cache_entry_for(self, tool_id: str, tool_version: str, entry: RAW_CACHED_JSON) -> None:
        cache_target = self._cache_target(tool_id, tool_version)
        parent_directory = os.path.dirname(cache_target)
        if not os.path.exists(parent_directory):
            os.makedirs(parent_directory)
        with open(cache_target, "w") as f:
            json.dump(entry, f)
