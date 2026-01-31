"""
High-level Mercurial operations for test fixtures.

This module provides a helper class for performing hg operations against a running
Tool Shed server, useful for creating test fixtures that require direct hg push
(bypassing the upload API) to simulate realistic developer workflows.
"""

import os
import subprocess
from urllib.parse import urlparse

from galaxy.util import unicodify

from tool_shed.util import hg_util


class HgRepositoryOperations:
    """
    High-level hg operations for test fixtures.

    This class wraps lower-level hg utilities to provide a convenient interface
    for cloning, modifying, and pushing repositories during tests.
    """

    def __init__(self, shed_url: str, username: str, password: str):
        """
        Initialize with Tool Shed connection details.

        Args:
            shed_url: Base URL of the Tool Shed (e.g., "http://localhost:9009")
            username: Username for authentication
            password: Password for authentication
        """
        self.shed_url = shed_url.rstrip("/")
        self.username = username
        self.password = password

    def clone_repo(self, owner: str, name: str, dest_dir: str) -> str:
        """
        Clone a repository from the Tool Shed.

        Args:
            owner: Repository owner username
            name: Repository name
            dest_dir: Destination directory for the clone

        Returns:
            Path to the cloned repository

        Raises:
            Exception: If clone fails
        """
        url = f"{self.shed_url}/repos/{owner}/{name}"
        success, msg = hg_util.clone_repository(url, dest_dir, "tip")
        if not success:
            raise Exception(f"Clone failed: {msg}")
        return dest_dir

    def add_and_commit(self, repo_path: str, files: dict[str, str], message: str) -> None:
        """
        Add files and commit them to a local repository.

        Args:
            repo_path: Path to the local repository
            files: Dict mapping relative paths to file contents
            message: Commit message

        Raises:
            Exception: If add or commit fails
        """
        for rel_path, content in files.items():
            full_path = os.path.join(repo_path, rel_path)
            dir_path = os.path.dirname(full_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
            hg_util.add_changeset(repo_path, rel_path)
        hg_util.commit_changeset(repo_path, ".", self.username, message)

    def push(self, repo_path: str, owner: str, name: str) -> None:
        """
        Push local repository changes to the Tool Shed.

        This bypasses the upload API and pushes directly via hg protocol,
        which does NOT create RepositoryMetadata records. Use this to test
        scenarios where metadata needs to be reset/created.

        Args:
            repo_path: Path to the local repository
            owner: Repository owner username
            name: Repository name

        Raises:
            Exception: If push fails (except "no changes found" which is ok)
        """
        url = f"http://{self.username}:{self.password}@{self._host_port}/repos/{owner}/{name}"
        self._push_repository(repo_path, url)

    @property
    def _host_port(self) -> str:
        """Extract host:port from shed_url."""
        parsed = urlparse(self.shed_url)
        return f"{parsed.hostname}:{parsed.port}"

    @staticmethod
    def _push_repository(repo_path: str, dest_url: str) -> None:
        """
        Push repository changes to a remote destination.

        Args:
            repo_path: Path to the local repository
            dest_url: URL to push to (may include credentials)

        Raises:
            Exception: If push fails (except "no changes found" which is ok)
        """
        try:
            subprocess.check_output(
                ["hg", "push", dest_url],
                stderr=subprocess.STDOUT,
                cwd=repo_path,
            )
        except subprocess.CalledProcessError as e:
            output = unicodify(e.output)
            # returncode 1 with "no changes found" means nothing to push - that's ok
            if e.returncode == 1 and "no changes found" in output:
                return
            raise Exception(f"Error pushing repository: {output}")
