import logging
import os
from threading import Lock
from typing import (
    Optional,
    TYPE_CHECKING,
    Union,
)

from galaxy.util import unicodify
from galaxy.util.hash_util import md5_hash_file

if TYPE_CHECKING:
    from galaxy.tools import Tool
    from galaxy.util.path import StrPath

log = logging.getLogger(__name__)


class ToolCache:
    """
    Cache tool definitions to allow quickly reloading the whole
    toolbox.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._hash_by_tool_paths: dict[str, ToolHash] = {}
        self._tools_by_path: dict[str, Tool] = {}
        self._tool_paths_by_id: dict[str, StrPath] = {}
        self._new_tool_ids: set[str] = set()
        self._removed_tool_ids: set[str] = set()
        self._removed_tools_by_path: dict[str, Tool] = {}
        self._hashes_initialized = False

    def assert_hashes_initialized(self) -> None:
        if not self._hashes_initialized:
            for tool_hash in self._hash_by_tool_paths.values():
                tool_hash.hash  # noqa: B018
            self._hashes_initialized = True

    def cleanup(self) -> list[str]:
        """
        Remove uninstalled tools from tool cache if they are not on disk anymore or if their content has changed.

        Returns list of tool_ids that have been removed.
        """
        removed_tool_ids: list[str] = []
        try:
            with self._lock:
                paths_to_cleanup = {
                    (path, tool) for path, tool in self._tools_by_path.items() if self._should_cleanup(path)
                }
                for config_filename, tool in paths_to_cleanup:
                    del self._hash_by_tool_paths[config_filename]
                    if os.path.exists(config_filename):
                        # This tool has probably been broken while editing on disk
                        # We record it here, so that we can recover it
                        self._removed_tools_by_path[config_filename] = self._tools_by_path[config_filename]
                    del self._tools_by_path[config_filename]
                    tool_ids = tool.all_ids
                    for tool_id in tool_ids:
                        if tool_id in self._tool_paths_by_id:
                            del self._tool_paths_by_id[tool_id]
                    removed_tool_ids.extend(tool_ids)
                for tool_id in removed_tool_ids:
                    self._removed_tool_ids.add(tool_id)
                    if tool_id in self._new_tool_ids:
                        self._new_tool_ids.remove(tool_id)
        except Exception as e:
            log.debug("Exception while checking tools to remove from cache: %s", unicodify(e))
            # If by chance the file is being removed while calculating the hash or modtime
            # we don't want the thread to die.
        if removed_tool_ids:
            log.debug(f"Removed the following tools from cache: {removed_tool_ids}")
        return removed_tool_ids

    def _should_cleanup(self, config_filename: str) -> bool:
        """Return True if `config_filename` does not exist or if modtime and hash have changes, else return False."""
        try:
            new_mtime = os.path.getmtime(config_filename)
            tool_hash = self._hash_by_tool_paths.get(config_filename)
            if tool_hash and tool_hash.modtime < new_mtime:
                if not tool_hash.hash == md5_hash_file(config_filename):
                    return True
                else:
                    # No change of content, so not necessary to calculate the md5 checksum every time
                    tool_hash.modtime = new_mtime
            tool = self._tools_by_path[config_filename]
            for macro_path in tool._macro_paths:
                new_mtime = os.path.getmtime(macro_path)
                if (macro_hash := self._hash_by_tool_paths.get(str(macro_path))) and macro_hash.modtime < new_mtime:
                    return True
        except FileNotFoundError:
            return True
        return False

    def get_tool(self, config_filename: "StrPath") -> Union["Tool", None]:
        """Get the tool at `config_filename` from the cache if the tool is up to date."""
        return self._tools_by_path.get(str(config_filename))

    def get_removed_tool(self, config_filename: "StrPath") -> Union["Tool", None]:
        return self._removed_tools_by_path.get(str(config_filename))

    def get_tool_by_id(self, tool_id: str) -> Union["Tool", None]:
        """Get the tool with the id `tool_id` from the cache if the tool is up to date."""
        if tool_path := self._tool_paths_by_id.get(tool_id):
            return self.get_tool(tool_path)
        return None

    def expire_tool(self, tool_id: str) -> None:
        with self._lock:
            if tool_id in self._tool_paths_by_id:
                config_filename = str(self._tool_paths_by_id[tool_id])
                del self._hash_by_tool_paths[config_filename]
                del self._tool_paths_by_id[tool_id]
                del self._tools_by_path[config_filename]
                if tool_id in self._new_tool_ids:
                    self._new_tool_ids.remove(tool_id)

    def cache_tool(self, config_filename: "StrPath", tool: "Tool") -> None:
        tool_id = str(tool.id)
        # We defer hashing of the config file if we haven't called assert_hashes_initialized.
        # This allows startup to occur without having to read in and hash all tool and macro files
        lazy_hash = not self._hashes_initialized
        with self._lock:
            self._hash_by_tool_paths[str(config_filename)] = ToolHash(config_filename, lazy_hash=lazy_hash)
            self._tool_paths_by_id[tool_id] = config_filename
            self._tools_by_path[str(config_filename)] = tool
            self._new_tool_ids.add(tool_id)
            for macro_path in tool._macro_paths:
                self._hash_by_tool_paths[str(macro_path)] = ToolHash(macro_path, lazy_hash=lazy_hash)

    def reset_status(self) -> None:
        """
        Reset tracking of new and newly disabled tools.
        """
        with self._lock:
            self._new_tool_ids = set()
            self._removed_tool_ids = set()
            self._removed_tools_by_path = {}


class ToolHash:
    def __init__(self, path: "StrPath", modtime: Optional[float] = None, lazy_hash: bool = False) -> None:
        self.path = path
        self.modtime = modtime or os.path.getmtime(path)
        self._tool_hash: Optional[str] = None
        if not lazy_hash:
            self.hash  # noqa: B018

    @property
    def hash(self) -> Union[str, None]:
        if self._tool_hash is None:
            self._tool_hash = md5_hash_file(self.path)
        return self._tool_hash
