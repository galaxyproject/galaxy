import logging
import os
import subprocess
from typing import (
    Optional,
    Tuple,
)

from galaxy.tool_shed.util import basic_util
from galaxy.util import unicodify

log = logging.getLogger(__name__)

INITIAL_CHANGELOG_HASH = "000000000000"


def clone_repository(repository_clone_url: str, repository_file_dir: str, ctx_rev=None) -> Tuple[bool, Optional[str]]:
    """
    Clone the repository up to the specified changeset_revision.  No subsequent revisions will be
    present in the cloned repository.
    """
    cmd = ["hg", "clone", "--stream"]
    if ctx_rev:
        cmd.extend(["-r", str(ctx_rev)])
    cmd.extend([repository_clone_url, repository_file_dir])
    # Make sure the destination path actually exists before attempting to clone
    if not os.path.exists(repository_file_dir):
        os.makedirs(repository_file_dir)
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        return True, None
    except Exception as e:
        error_message = f"Error cloning repository: {unicodify(e)}"
        if isinstance(e, subprocess.CalledProcessError):
            error_message += f"\nOutput was:\n{unicodify(e.output)}"
        log.error(error_message)
        return False, error_message


def copy_file_from_manifest(repo, changeset_revision, filename, dir):
    """
    Copy the latest version of the file named filename from the repository manifest to the directory
    to which dir refers.
    """
    for changeset in reversed_upper_bounded_changelog(repo, changeset_revision):
        changeset_ctx = repo[changeset]
        fctx = get_file_context_from_ctx(changeset_ctx, filename)
        if fctx and fctx not in ["DELETED"]:
            file_path = os.path.join(dir, filename)
            fh = open(file_path, "wb")
            fh.write(fctx.data())
            fh.close()
            return file_path
    return None


def get_changectx_for_changeset(repo, changeset_revision, **kwd):
    """Retrieve a specified changectx from a repository."""
    for changeset in repo.changelog:
        ctx = repo[changeset]
        if str(ctx) == changeset_revision:
            return ctx
    return None


def get_config_from_disk(config_file: str, relative_install_dir: str) -> Optional[str]:
    for root, _dirs, files in os.walk(relative_install_dir):
        if root.find(".hg") < 0:
            for name in files:
                if name == config_file:
                    return os.path.abspath(os.path.join(root, name))
    return None


def get_ctx_file_path_from_manifest(filename, repo, changeset_revision):
    """
    Get the ctx file path for the latest revision of filename from the repository manifest up
    to the value of changeset_revision.
    """
    stripped_filename = basic_util.strip_path(filename)
    for changeset in reversed_upper_bounded_changelog(repo, changeset_revision):
        manifest_ctx = repo[changeset]
        for ctx_file in manifest_ctx.files():
            ctx_file_name = basic_util.strip_path(unicodify(ctx_file))
            if ctx_file_name == stripped_filename:
                return manifest_ctx, ctx_file
    return None, None


def get_file_context_from_ctx(ctx, filename):
    """Return the mercurial file context for a specified file."""
    # We have to be careful in determining if we found the correct file because multiple files with
    # the same name may be in different directories within ctx if the files were moved within the change
    # set.  For example, in the following ctx.files() list, the former may have been moved to the latter:
    # ['tmap_wrapper_0.0.19/tool_data_table_conf.xml.sample', 'tmap_wrapper_0.3.3/tool_data_table_conf.xml.sample'].
    # Another scenario is that the file has been deleted.
    deleted = False
    filename = basic_util.strip_path(filename)
    for ctx_file in ctx.files():
        ctx_file_name = basic_util.strip_path(unicodify(ctx_file))
        if filename == ctx_file_name:
            try:
                # If the file was moved, its destination will be returned here.
                fctx = ctx[ctx_file]
                return fctx
            except LookupError:
                # Set deleted for now, and continue looking in case the file was moved instead of deleted.
                deleted = True
    if deleted:
        return "DELETED"
    return None


def pull_repository(repo_path, repository_clone_url, ctx_rev):
    """Pull changes from a remote repository to a local one."""
    try:
        subprocess.check_output(
            ["hg", "pull", "-r", ctx_rev, repository_clone_url], stderr=subprocess.STDOUT, cwd=repo_path
        )
    except Exception as e:
        error_message = f"Error pulling revision '{ctx_rev}': {unicodify(e)}"
        if isinstance(e, subprocess.CalledProcessError):
            error_message += f"\nOutput was:\n{unicodify(e.output)}"
        raise Exception(error_message)


def reversed_lower_upper_bounded_changelog(
    repo, excluded_lower_bounds_changeset_revision, included_upper_bounds_changeset_revision
):
    """
    Return a reversed list of changesets in the repository changelog after the excluded_lower_bounds_changeset_revision,
    but up to and including the included_upper_bounds_changeset_revision.  The value of excluded_lower_bounds_changeset_revision
    will be the value of INITIAL_CHANGELOG_HASH if no valid changesets exist before included_upper_bounds_changeset_revision.
    """
    # To set excluded_lower_bounds_changeset_revision, calling methods should do the following, where the value
    # of changeset_revision is a downloadable changeset_revision.
    # excluded_lower_bounds_changeset_revision = \
    #     metadata_util.get_previous_metadata_changeset_revision(app, repository, changeset_revision, downloadable=?)
    if excluded_lower_bounds_changeset_revision == INITIAL_CHANGELOG_HASH:
        appending_started = True
    else:
        appending_started = False
    reversed_changelog = []
    for changeset in repo.changelog:
        changeset_hash = str(repo[changeset])
        if appending_started:
            reversed_changelog.insert(0, changeset)
        if changeset_hash == excluded_lower_bounds_changeset_revision and not appending_started:
            appending_started = True
        if changeset_hash == included_upper_bounds_changeset_revision:
            break
    return reversed_changelog


def reversed_upper_bounded_changelog(repo, included_upper_bounds_changeset_revision):
    """
    Return a reversed list of changesets in the repository changelog up to and including the
    included_upper_bounds_changeset_revision.
    """
    return reversed_lower_upper_bounded_changelog(
        repo, INITIAL_CHANGELOG_HASH, included_upper_bounds_changeset_revision
    )


def update_repository(repo_path, ctx_rev=None):
    """
    Update the cloned repository to changeset_revision.  It is critical that the installed repository is updated to the desired
    changeset_revision before metadata is set because the process for setting metadata uses the repository files on disk.
    """
    # TODO: We may have files on disk in the repo directory that aren't being tracked, so they must be removed.
    # The codes used to show the status of files are as follows.
    # M = modified
    # A = added
    # R = removed
    # C = clean
    # ! = deleted, but still tracked
    # ? = not tracked
    # I = ignored
    # It would be nice if we could use mercurial's purge extension to remove untracked files.  The problem is that
    # purging is not supported by the mercurial API.
    cmd = ["hg", "update"]
    if ctx_rev:
        cmd.extend(["-r", ctx_rev])
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT, cwd=repo_path)
    except Exception as e:
        error_message = f"Error updating repository: {unicodify(e)}"
        if isinstance(e, subprocess.CalledProcessError):
            error_message += f"\nOutput was:\n{unicodify(e.output)}"
        raise Exception(error_message)


__all__ = (
    "clone_repository",
    "copy_file_from_manifest",
    "get_changectx_for_changeset",
    "get_config_from_disk",
    "get_ctx_file_path_from_manifest",
    "get_file_context_from_ctx",
    "pull_repository",
    "reversed_lower_upper_bounded_changelog",
    "reversed_upper_bounded_changelog",
    "update_repository",
)
