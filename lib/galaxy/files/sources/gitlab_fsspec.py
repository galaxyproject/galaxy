"""Writable fsspec filesystem for GitLab projects.

``arcfs.fs.GitLabARCFileSystem`` reads any GitLab project but writes the way an ARC takes data:
through Git LFS, onto a generated branch, behind a merge request. A GitLab user exporting a file
expects a commit on the branch instead, so this subclass writes that way. Same shape as
``github_fsspec.py``, which adds a write to fsspec's read-only GitHub filesystem for the same
reason.

The parts that decide what a commit contains are plain functions rather than methods, so they
run without the optional ``arcfs-fsspec`` package, which CI does not install.
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

#: What a commit may carry. Far below GitLab's own 300 MB ceiling: the content is read,
#: base64-encoded and serialised into the request body, so several copies of the file are
#: resident at once, and GitLab rate limits requests above 20 MB anyway. An ARC file source
#: streams through Git LFS and has no such limit.
MAX_COMMIT_BYTES = 20 * 1024 * 1024


def commit_actions(inside: str, content: str, existing: dict | None) -> list[dict]:
    """Build the commit actions that replace or create the file.

    An existing file is deleted and created again in one commit rather than updated, because
    GitLab runs its Git LFS transformer only for ``create``: an ``update`` onto a path
    ``.gitattributes`` marks as LFS commits raw bytes where git expects a pointer, and nothing
    can read the repository afterwards. Both actions ride in one commit, so the file is never
    missing in between.
    """
    actions: list[dict] = []
    if existing is not None:
        delete: dict = {"action": "delete", "file_path": inside}
        # Refuses the delete if the file moved on since it was read, so two exports of one path
        # cannot silently lose one.
        if existing.get("last_commit_id"):
            delete["last_commit_id"] = existing["last_commit_id"]
        actions.append(delete)

    create: dict = {"action": "create", "file_path": inside, "content": content, "encoding": "base64"}
    if existing is not None and existing.get("execute_filemode"):
        create["execute_filemode"] = True
    actions.append(create)
    return actions


async def refuse_a_directory(client, repo_id: int, inside: str, branch: str) -> None:
    """Refuse a target naming a folder, which a commit would replace along with its contents.

    The files endpoint answers 404 for a folder exactly as for a path that is not there. The tree
    endpoint tells them apart, but differently per version: 404 from GitLab 17.7 on, ``200 []``
    before it. Git has no empty trees, so the entries decide it either way.
    """
    try:
        entries, _ = await client.retrieve_project_level_page(repo_id, inside, ref=branch, per_page=1)
    except FileNotFoundError:
        return
    if not entries:
        return
    raise MessageException(
        f"{inside} is a folder in this project, not a file. Exporting to it would "
        "replace the folder and everything inside it. Name a file within it instead."
    )


def check_commit_size(size: int, rpath: str) -> None:
    """Refuse a file GitLab will not carry inside a commit request."""
    if size > MAX_COMMIT_BYTES:
        raise MessageException(
            f"{rpath} is {size} bytes, more than the {MAX_COMMIT_BYTES} a GitLab commit can "
            "carry. An ARC file source uploads through Git LFS and has no such limit."
        )


if GitLabARCFileSystem is not None:

    class WritableGitLabFileSystem(GitLabARCFileSystem):
        """``GitLabARCFileSystem`` that commits a file instead of exporting it the ARC way."""

        async def _put_file(self, lpath, rpath, **kwargs):
            """Commit one local file onto a branch."""
            repo, inside = await self._resolve(rpath, refresh=bool(kwargs.pop("refresh", False)), **kwargs)
            if not inside:
                raise IsADirectoryError(rpath)

            path = pathlib.Path(lpath)
            check_commit_size(path.stat().st_size, rpath)
            loop = asyncio.get_running_loop()
            raw = await loop.run_in_executor(None, path.read_bytes)
            # The file may have grown since it was measured; the bytes being sent are what count.
            check_commit_size(len(raw), rpath)

            branch = kwargs.get("ref") or await self.client.get_default_branch(repo["id"])

            existing = await self._existing_file(repo["id"], inside, branch)
            if existing is None:
                await refuse_a_directory(self.client, repo["id"], inside, branch)
            message = (
                kwargs.get("commit_message") or f"{'Update' if existing else 'Add'} {inside} (uploaded from Galaxy)"
            )

            actions = commit_actions(inside, base64.b64encode(raw).decode("ascii"), existing)
            del raw  # the encoded copy is what gets sent; two of a large file is enough
            await self.client.create_commit(repo["id"], branch, message, actions)
            self.dircache.clear()

        def _open(self, path, mode="rb", **kwargs):
            """Refuse a write through ``open``, which the inherited one sends the ARC way.

            The inherited object commits only from ``__aexit__``, so an ordinary write-then-close
            discards the data anyway. The test is for write intent, since "r+b" is read-write.
            """
            if set(mode) & set("wax+"):
                raise NotImplementedError(
                    "This file source commits whole files. Use put_file rather than open(..., 'wb')."
                )
            return super()._open(path, mode=mode, **kwargs)

        async def open_async(self, path, mode="rb", **kwargs):
            """Refuse an async write for the same reason ``_open`` does."""
            if set(mode) & set("wax+"):
                raise NotImplementedError(
                    "This file source commits whole files. Use put_file rather than open_async(..., 'wb')."
                )
            return await super().open_async(path, mode=mode, **kwargs)

        async def _existing_file(self, repo_id: int, inside: str, branch: str) -> dict | None:
            """Return what a replacement needs, or ``None`` if the branch has no such path.

            HEAD rather than GET: the JSON files endpoint answers with the whole file
            base64-encoded, so replacing a small dataset over a large existing blob read and
            parsed hundreds of megabytes to obtain two header-sized fields.
            """
            session = await self.client._ensure()
            url = self.client._repository_file_url(repo_id, inside)
            async with session.head(url, params={"ref": branch}) as answer:
                if answer.status == 404:
                    return None
                answer.raise_for_status()
                headers = answer.headers
            return {
                "last_commit_id": headers.get("X-Gitlab-Last-Commit-Id"),
                # Headers are text, and the string "false" is true.
                "execute_filemode": headers.get("X-Gitlab-Execute-Filemode", "").lower() == "true",
            }

else:
    WritableGitLabFileSystem = None  # type: ignore[assignment, misc, unused-ignore]


__all__ = (
    "MAX_COMMIT_BYTES",
    "WritableGitLabFileSystem",
    "check_commit_size",
    "commit_actions",
    "refuse_a_directory",
)
