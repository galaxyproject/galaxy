import json
import logging
import os
import shutil
import sqlite3
import tempfile
import zlib
from threading import Lock

from sqlitedict import SqliteDict

from galaxy.util import unicodify
from galaxy.util.hash_util import md5_hash_file

log = logging.getLogger(__name__)

CURRENT_TOOL_CACHE_VERSION = 0


def encoder(obj):
    return sqlite3.Binary(zlib.compress(json.dumps(obj).encode("utf-8")))


def decoder(obj):
    return json.loads(zlib.decompress(bytes(obj)).decode("utf-8"))


class ToolDocumentCache:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.cache_file = os.path.join(self.cache_dir, "cache.sqlite")
        self.writeable_cache_file = None
        self._cache = None
        self.disabled = False
        self._get_cache(create_if_necessary=True)

    def close(self):
        self._cache and self._cache.close()

    def _get_cache(self, flag="r", create_if_necessary=False):
        try:
            if create_if_necessary and not os.path.exists(self.cache_file):
                # Create database if necessary using 'c' flag
                self._cache = SqliteDict(self.cache_file, flag="c", encode=encoder, decode=decoder, autocommit=False)
                if flag == "r":
                    self._cache.flag = flag
            else:
                cache_file = self.writeable_cache_file.name if self.writeable_cache_file else self.cache_file
                self._cache = SqliteDict(cache_file, flag=flag, encode=encoder, decode=decoder, autocommit=False)
        except sqlite3.OperationalError:
            log.warning("Tool document cache unavailable")
            self._cache = None
            self.disabled = True

    @property
    def cache_file_is_writeable(self):
        return os.access(self.cache_file, os.W_OK)

    def reopen_ro(self):
        self._get_cache(flag="r")
        self.writeable_cache_file = None

    def get(self, config_file):
        try:
            tool_document = self._cache.get(config_file)
        except sqlite3.OperationalError:
            log.debug("Tool document cache unavailable")
            return None
        if not tool_document:
            return None
        if tool_document.get("tool_cache_version") != CURRENT_TOOL_CACHE_VERSION:
            return None
        if self.cache_file_is_writeable:
            for path, modtime in tool_document["paths_and_modtimes"].items():
                if os.path.getmtime(path) != modtime:
                    return None
        return tool_document

    def _make_writable(self):
        if not self.writeable_cache_file:
            self.writeable_cache_file = tempfile.NamedTemporaryFile(
                dir=self.cache_dir, suffix="cache.sqlite.tmp", delete=False
            )
            if os.path.exists(self.cache_file):
                shutil.copy(self.cache_file, self.writeable_cache_file.name)
            self._get_cache(flag="c")

    def persist(self):
        if self.writeable_cache_file:
            self._cache.commit()
            os.rename(self.writeable_cache_file.name, self.cache_file)
            self.reopen_ro()

    def set(self, config_file, tool_source):
        try:
            if self.cache_file_is_writeable:
                self._make_writable()
                to_persist = {
                    "document": tool_source.to_string(),
                    "macro_paths": tool_source.macro_paths,
                    "paths_and_modtimes": tool_source.paths_and_modtimes(),
                    "tool_cache_version": CURRENT_TOOL_CACHE_VERSION,
                }
                try:
                    self._cache[config_file] = to_persist
                except RuntimeError:
                    log.debug("Tool document cache not writeable")
        except sqlite3.OperationalError:
            log.debug("Tool document cache unavailable")

    def delete(self, config_file):
        if self.cache_file_is_writeable:
            self._make_writable()
            try:
                del self._cache[config_file]
            except (KeyError, RuntimeError):
                pass

    def __del__(self):
        if self.writeable_cache_file:
            try:
                os.unlink(self.writeable_cache_file.name)
            except Exception:
                pass


class ToolCache:
    """
    Cache tool definitions to allow quickly reloading the whole
    toolbox.
    """

    def __init__(self):
        self._lock = Lock()
        self._hash_by_tool_paths = {}
        self._tools_by_path = {}
        self._tool_paths_by_id = {}
        self._macro_paths_by_id = {}
        self._new_tool_ids = set()
        self._removed_tool_ids = set()
        self._removed_tools_by_path = {}
        self._hashes_initialized = False

    def assert_hashes_initialized(self):
        if not self._hashes_initialized:
            for tool_hash in self._hash_by_tool_paths.values():
                tool_hash.hash
            self._hashes_initialized = True

    def cleanup(self):
        """
        Remove uninstalled tools from tool cache if they are not on disk anymore or if their content has changed.

        Returns list of tool_ids that have been removed.
        """
        removed_tool_ids = []
        try:
            with self._lock:
                persist_tool_document_cache = False
                paths_to_cleanup = {
                    (path, tool) for path, tool in self._tools_by_path.items() if self._should_cleanup(path)
                }
                for config_filename, tool in paths_to_cleanup:
                    tool.remove_from_cache()
                    persist_tool_document_cache = True
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
                if persist_tool_document_cache:
                    tool.app.toolbox.persist_cache()
        except Exception as e:
            log.debug("Exception while checking tools to remove from cache: %s", unicodify(e))
            # If by chance the file is being removed while calculating the hash or modtime
            # we don't want the thread to die.
        if removed_tool_ids:
            log.debug(f"Removed the following tools from cache: {removed_tool_ids}")
        return removed_tool_ids

    def _should_cleanup(self, config_filename):
        """Return True if `config_filename` does not exist or if modtime and hash have changes, else return False."""
        try:
            new_mtime = os.path.getmtime(config_filename)
            tool_hash = self._hash_by_tool_paths.get(config_filename)
            if tool_hash.modtime < new_mtime:
                if md5_hash_file(config_filename) != tool_hash.hash:
                    return True
            tool = self._tools_by_path[config_filename]
            for macro_path in tool._macro_paths:
                new_mtime = os.path.getmtime(macro_path)
                if self._hash_by_tool_paths.get(macro_path).modtime < new_mtime:
                    return True
        except FileNotFoundError:
            return True
        return False

    def get_tool(self, config_filename):
        """Get the tool at `config_filename` from the cache if the tool is up to date."""
        return self._tools_by_path.get(config_filename, None)

    def get_removed_tool(self, config_filename):
        return self._removed_tools_by_path.get(config_filename)

    def get_tool_by_id(self, tool_id):
        """Get the tool with the id `tool_id` from the cache if the tool is up to date."""
        return self.get_tool(self._tool_paths_by_id.get(tool_id))

    def expire_tool(self, tool_id):
        with self._lock:
            if tool_id in self._tool_paths_by_id:
                config_filename = self._tool_paths_by_id[tool_id]
                del self._hash_by_tool_paths[config_filename]
                del self._tool_paths_by_id[tool_id]
                del self._tools_by_path[config_filename]
                if tool_id in self._new_tool_ids:
                    self._new_tool_ids.remove(tool_id)

    def cache_tool(self, config_filename, tool):
        tool_id = str(tool.id)
        # We defer hashing of the config file if we haven't called assert_hashes_initialized.
        # This allows startup to occur without having to read in and hash all tool and macro files
        lazy_hash = not self._hashes_initialized
        with self._lock:
            self._hash_by_tool_paths[config_filename] = ToolHash(config_filename, lazy_hash=lazy_hash)
            self._tool_paths_by_id[tool_id] = config_filename
            self._tools_by_path[config_filename] = tool
            self._new_tool_ids.add(tool_id)
            for macro_path in tool._macro_paths:
                self._hash_by_tool_paths[macro_path] = ToolHash(macro_path, lazy_hash=lazy_hash)
                if tool_id not in self._macro_paths_by_id:
                    self._macro_paths_by_id[tool_id] = {macro_path}
                else:
                    self._macro_paths_by_id[tool_id].add(macro_path)

    def reset_status(self):
        """
        Reset tracking of new and newly disabled tools.
        """
        with self._lock:
            self._new_tool_ids = set()
            self._removed_tool_ids = set()
            self._removed_tools_by_path = {}


class ToolHash:
    def __init__(self, path, modtime=None, lazy_hash=False):
        self.path = path
        self.modtime = modtime or os.path.getmtime(path)
        self._tool_hash = None
        if not lazy_hash:
            self.hash

    @property
    def hash(self):
        if self._tool_hash is None:
            self._tool_hash = md5_hash_file(self.path)
        return self._tool_hash
