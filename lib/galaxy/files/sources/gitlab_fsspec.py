"""Writable fsspec filesystem for GitLab projects.

``arcfs.fs.GitLabARCFileSystem`` reads any GitLab project, but it writes the one way an ARC
takes data: the file goes to the instance's Git LFS store, a pointer to it is committed on a
generated branch, and a merge request is opened. That is right for an ARC and wrong for a
project, where a user exporting a file expects a commit on the branch they chose.

This module subclasses it to write the second way. The ARC file source keeps the filesystem it
has; the GitLab file source (``gitlab.py``) uses this one, so the two differ by which
filesystem they open rather than by any logic in the plugins.

The same shape as ``github_fsspec.py``, and for the same reason: the upstream filesystem does
not write, so the write lives here until it does. Once ``arcfs-fsspec`` grows a plain-commit
path of its own, this module becomes a thin alias and then goes away.
"""

import asyncio
import base64
import logging
import pathlib

from galaxy.exceptions import MessageException

try:
    from arcfs.fs import GitLabARCFileSystem
except ImportError:
    GitLabARCFileSystem = None  # type: ignore[assignment, misc, unused-ignore]

log = logging.getLogger(__name__)

# GitLab rejects a commit request larger than this with 413 and documents the default as 300 MB.
# Self-managed instances can lower it with GITLAB_COMMITS_MAX_REQUEST_SIZE_BYTES, so an instance
# may refuse less. https://docs.gitlab.com/administration/instance_limits/#commits-and-files-apis
GITLAB_MAX_COMMIT_REQUEST_BYTES = 314_572_800

# The content rides base64-encoded inside the request body, which spends four bytes for every
# three, so the file may be three quarters of what the request may be. GitLab also rate limits
# requests over 20 MB, and both forms of the file are held in memory at once, so this is a
# ceiling rather than a size to aim for.
MAX_COMMIT_BYTES = GITLAB_MAX_COMMIT_REQUEST_BYTES * 3 // 4


def commit_actions(inside: str, content: str, existing: dict | None) -> list[dict]:
    """Build the commit actions that replace or create the file.

    A file that is already there is deleted and created again in the same commit rather than
    updated. GitLab runs the Git LFS transformer only for ``create`` actions, so an ``update``
    onto a path ``.gitattributes`` marks as LFS commits the raw bytes where git expects a
    pointer, which no reader can make sense of afterwards. Both actions ride in one commit, so
    the file is never missing in between.

    Args:
        inside: Repository-internal path the file takes.
        content: The file, base64-encoded.
        existing: GitLab's metadata for the file already at that path, or ``None``.

    Returns:
        The ``actions`` list for one commit.
    """
    actions: list[dict] = []
    if existing is not None:
        delete: dict = {"action": "delete", "file_path": inside}
        # GitLab refuses the delete if the file moved on since it was read, which is what stops
        # two exports of the same path from silently losing one of them.
        if existing.get("last_commit_id"):
            delete["last_commit_id"] = existing["last_commit_id"]
        actions.append(delete)

    create: dict = {
        "action": "create",
        "file_path": inside,
        "content": content,
        "encoding": "base64",
    }
    # Creating the file afresh would otherwise drop the execute bit the old one carried.
    if existing is not None and existing.get("execute_filemode"):
        create["execute_filemode"] = True
    actions.append(create)
    return actions


def check_commit_size(size: int, rpath: str) -> None:
    """Refuse a file GitLab will not carry inside a commit request.

    Raises:
        MessageException: If the file is above what a commit request may hold.
    """
    if size > MAX_COMMIT_BYTES:
        raise MessageException(
            f"{rpath} is {size} bytes, more than the {MAX_COMMIT_BYTES} a GitLab commit can "
            "carry. GitLab sends the content inside the request body and refuses requests "
            "beyond its own limit, so this cannot be uploaded to a GitLab project. An ARC file "
            "source uploads through Git LFS and has no such limit."
        )


if GitLabARCFileSystem is not None:

    class WritableGitLabFileSystem(GitLabARCFileSystem):
        """``GitLabARCFileSystem`` that commits a file instead of exporting it the ARC way."""

        async def _put_file(self, lpath, rpath, **kwargs):
            """Commit one local file onto a branch.

            Args:
                lpath: Local source path.
                rpath: Remote target path, ``group/project:-:folder/file``.
                **kwargs: ``ref`` selects the branch, defaulting to the project's default
                    branch, and ``commit_message`` overrides the generated message.

            Raises:
                IsADirectoryError: If the target names a project rather than a file inside one.
                MessageException: If the target names a folder inside a project, or if the file
                    is too large for GitLab to accept in a commit.
            """
            repo, inside = await self._resolve(rpath, refresh=bool(kwargs.pop("refresh", False)), **kwargs)
            if not inside:
                raise IsADirectoryError(rpath)

            path = pathlib.Path(lpath)
            check_commit_size(path.stat().st_size, rpath)
            loop = asyncio.get_running_loop()
            raw = await loop.run_in_executor(None, path.read_bytes)
            # The file may have grown since it was measured, and it is the bytes being sent that
            # have to fit, so the check that matters is this one.
            check_commit_size(len(raw), rpath)

            branch = kwargs.get("ref")
            if branch is None:
                branch = await self.client.get_default_branch(repo["id"])

            existing = await self._existing_file(repo["id"], inside, branch)
            if existing is None:
                await self._refuse_a_directory(repo["id"], inside, branch)
            message = kwargs.get("commit_message")
            if message is None:
                message = f"{'Update' if existing else 'Add'} {inside} (uploaded from Galaxy)"

            await self.client.create_commit(
                repo["id"],
                branch,
                message,
                commit_actions(inside, base64.b64encode(raw).decode("ascii"), existing),
            )
            self.dircache.clear()

        async def _refuse_a_directory(self, repo_id: int, inside: str, branch: str) -> None:
            """Refuse a target naming a folder rather than a file inside one.

            Git stores a path as a blob or a tree and a commit may swap one for the other, so a
            create action against a folder replaces that folder and everything under it in a
            single commit, on whatever branch the export named. GitLab gives no warning: the
            files endpoint answers 404 for a folder exactly as it does for a path that is not
            there, so nothing earlier in this method can tell the two apart.

            The tree endpoint can: it answers with the entries for a folder and 404 for anything
            else, including a file. This costs a request, but only on the branch where the file
            is new, because a path that is already a file cannot also be a folder.
            """
            try:
                await self.client.retrieve_project_level_page(repo_id, inside, ref=branch, per_page=1)
            except FileNotFoundError:
                return
            raise MessageException(
                f"{inside} is a folder in this project, not a file. Exporting to it would "
                "replace the folder and everything inside it. Name a file within it instead."
            )

        async def _existing_file(self, repo_id: int, inside: str, branch: str) -> dict | None:
            """Return GitLab's metadata for the file, or ``None`` if the branch has no such path.

            This costs the file's own bytes, because the endpoint answers with the content
            base64-encoded and the backend offers nothing cheaper. It buys three things that
            each need a request otherwise: whether to create or replace, the commit id that
            makes the replacement safe against a concurrent write, and the execute bit.
            """
            try:
                return await self.client.get_file(repo_id, inside, branch)
            except FileNotFoundError:
                # Either the path is not on the branch or the repository has no commits at all;
                # both mean there is nothing to replace.
                return None

else:
    WritableGitLabFileSystem = None  # type: ignore[assignment, misc, unused-ignore]


__all__ = ("MAX_COMMIT_BYTES", "WritableGitLabFileSystem", "check_commit_size", "commit_actions")
