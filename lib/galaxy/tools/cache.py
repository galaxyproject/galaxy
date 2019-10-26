import logging
import os
from collections import defaultdict
from threading import Lock

from sqlalchemy.orm import (
    defer,
    joinedload,
)

from galaxy.util import unicodify
from galaxy.util.hash_util import md5_hash_file

log = logging.getLogger(__name__)


class ToolCache(object):
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
        self._mod_time_by_path = {}
        self._new_tool_ids = set()
        self._removed_tool_ids = set()
        self._removed_tools_by_path = {}

    def cleanup(self):
        """
        Remove uninstalled tools from tool cache if they are not on disk anymore or if their content has changed.

        Returns list of tool_ids that have been removed.
        """
        removed_tool_ids = []
        try:
            with self._lock:
                paths_to_cleanup = {path: tool.all_ids for path, tool in self._tools_by_path.items() if self._should_cleanup(path)}
                for config_filename, tool_ids in paths_to_cleanup.items():
                    del self._hash_by_tool_paths[config_filename]
                    if os.path.exists(config_filename):
                        # This tool has probably been broken while editing on disk
                        # We record it here, so that we can recover it
                        self._removed_tools_by_path[config_filename] = self._tools_by_path[config_filename]
                    del self._tools_by_path[config_filename]
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
            pass
        if removed_tool_ids:
            log.debug("Removed the following tools from cache: %s" % removed_tool_ids)
        return removed_tool_ids

    def _should_cleanup(self, config_filename):
        """Return True if `config_filename` does not exist or if modtime and hash have changes, else return False."""
        if not os.path.exists(config_filename):
            return True
        new_mtime = os.path.getmtime(config_filename)
        if self._mod_time_by_path.get(config_filename) < new_mtime:
            if md5_hash_file(config_filename) != self._hash_by_tool_paths.get(config_filename):
                return True
        tool = self._tools_by_path[config_filename]
        for macro_path in tool._macro_paths:
            new_mtime = os.path.getmtime(macro_path)
            if self._mod_time_by_path.get(macro_path) < new_mtime:
                return True
        return False

    def get_tool(self, config_filename):
        """Get the tool at `config_filename` from the cache if the tool is up to date."""
        return self._tools_by_path.get(config_filename, None)

    def get_removed_tool(self, config_filename):
        return self._removed_tools_by_path.get(config_filename)

    def get_tool_by_id(self, tool_id):
        """Get the tool with the id `tool_id` from the cache if the tool is up to date. """
        return self.get_tool(self._tool_paths_by_id.get(tool_id))

    def expire_tool(self, tool_id):
        with self._lock:
            if tool_id in self._tool_paths_by_id:
                config_filename = self._tool_paths_by_id[tool_id]
                del self._hash_by_tool_paths[config_filename]
                del self._tool_paths_by_id[tool_id]
                del self._tools_by_path[config_filename]
                del self._mod_time_by_path[config_filename]
                if tool_id in self._new_tool_ids:
                    self._new_tool_ids.remove(tool_id)

    def cache_tool(self, config_filename, tool):
        tool_hash = md5_hash_file(config_filename)
        if tool_hash is None:
            return
        tool_id = str(tool.id)
        with self._lock:
            self._hash_by_tool_paths[config_filename] = tool_hash
            self._mod_time_by_path[config_filename] = os.path.getmtime(config_filename)
            self._tool_paths_by_id[tool_id] = config_filename
            self._tools_by_path[config_filename] = tool
            self._new_tool_ids.add(tool_id)
            for macro_path in tool._macro_paths:
                self._mod_time_by_path[macro_path] = os.path.getmtime(macro_path)
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


class ToolShedRepositoryCache(object):
    """
    Cache installed ToolShedRepository objects.
    """

    def __init__(self, app):
        self.app = app
        # Contains ToolConfRepository objects created from shed_tool_conf.xml entries
        self.local_repositories = []
        # Repositories loaded from database
        self.repositories = []
        self.repos_by_tuple = defaultdict(list)
        self.rebuild()

    def add_local_repository(self, repository):
        self.local_repositories.append(repository)
        self.repos_by_tuple[(repository.tool_shed, repository.owner, repository.name)].append(repository)

    def rebuild(self):
        self.repositories = self.app.install_model.context.current.query(self.app.install_model.ToolShedRepository).options(
            defer(self.app.install_model.ToolShedRepository.metadata),
            joinedload('tool_dependencies'),
        ).all()
        repos_by_tuple = defaultdict(list)
        for repository in self.repositories + self.local_repositories:
            repos_by_tuple[(repository.tool_shed, repository.owner, repository.name)].append(repository)
        self.repos_by_tuple = repos_by_tuple

    def get_installed_repository(self, tool_shed=None, name=None, owner=None, installed_changeset_revision=None, changeset_revision=None, repository_id=None):
        if repository_id:
            repos = [repo for repo in self.repositories if repo.id == repository_id]
            if repos:
                return repos[0]
            else:
                return None
        repos = self.repos_by_tuple[(tool_shed, owner, name)]
        for repo in repos:
            if installed_changeset_revision and repo.installed_changeset_revision != installed_changeset_revision:
                continue
            if changeset_revision and repo.changeset_revision != changeset_revision:
                continue
            return repo
        return None
